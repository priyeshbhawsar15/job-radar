"""Local isolated persistence-path verification script."""

import asyncio
import os
import tempfile
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func

temp_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
temp_db_path = temp_db_file.name
temp_db_file.close()

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{temp_db_path}"
os.environ["SETTINGS_FILE_PATH"] = f"{temp_db_path}.settings.json"

from job_radar.db.base import Base
from job_radar.db.models.board import Board, BoardRevision
from job_radar.db.models.candidate import CandidateJob, RunCandidate
from job_radar.db.models.handoff import HandoffOutbox, HandoffAttempt
from job_radar.db.seed import INITIAL_BOARDS, BLOCKED_BOARD_IDS, build_initial_revision_config
from job_radar.adapters.base import ExtractedCandidate
from job_radar.services.normalization import NormalizationService
from job_radar.services.handoff import HandoffProcessor, JobOpsClient
from job_radar.services.settings_store import load_settings, save_settings, AppSettingsModel
from job_radar.services.location import is_india_eligible


async def verify_isolated_persistence():
    print(f"Running isolated persistence verification against {temp_db_path}...")

    engine = create_async_engine(f"sqlite+aiosqlite:///{temp_db_path}", echo=False)
    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 1. Verify settings handoff_enabled=False
    settings = AppSettingsModel(handoff_enabled=False)
    save_settings(settings, Path(f"{temp_db_path}.settings.json"))
    loaded = load_settings(Path(f"{temp_db_path}.settings.json"))
    assert loaded.handoff_enabled is False, "Handoff must be False"
    print("✓ Setting readback verified: handoff_enabled=False")

    # 2. Seed all 102 boards
    async with async_session_factory() as session:
        for item in INITIAL_BOARDS:
            b_id, name, family = item[0], item[1], item[2]
            status = "draft" if b_id in BLOCKED_BOARD_IDS else "reviewed"
            board = Board(
                board_id=b_id,
                name=name,
                family=family,
                status=status,
                consecutive_parser_failures=0
            )
            session.add(board)
            await session.flush()

            cfg_json = build_initial_revision_config(item)
            rev = BoardRevision(
                board_id=b_id,
                revision_number=1,
                status=status,
                config_json=cfg_json
            )
            session.add(rev)
            await session.flush()
            board.current_revision_id = rev.revision_id

        await session.commit()

    # Read back 102 board rows and counts
    async with async_session_factory() as session:
        b_res = await session.execute(select(Board))
        all_boards = b_res.scalars().all()
        assert len(all_boards) == 102, f"Expected 102 boards, got {len(all_boards)}"

        rev_boards = [b for b in all_boards if b.status in ("reviewed", "active", "enabled")]
        draft_boards = [b for b in all_boards if b.status == "draft"]

        print(f"✓ Total board rows persisted: {len(all_boards)} (Reviewed: {len(rev_boards)}, Draft: {len(draft_boards)})")
        assert len(rev_boards) == 76, f"Expected 76 reviewed boards (37 baseline + 39 new), got {len(rev_boards)}"
        assert len(draft_boards) == 26, f"Expected 26 draft/blocked boards, got {len(draft_boards)}"

    # 3. Test NormalizationService & HandoffProcessor with Candidate India eligibility
    client = JobOpsClient()
    norm_service = NormalizationService(session_factory=async_session_factory)
    handoff_proc = HandoffProcessor(session_factory=async_session_factory, jobops_client=client)

    desc_sample = """About the Role:
We are looking for a Senior Software Engineer to join our core backend engineering team in Bengaluru, India.

Key Responsibilities:
- Design, build, and maintain high-performance microservices and RESTful API endpoints.
- Collaborate with product managers, system architects, and cross-functional engineering teams.

Qualifications & Requirements:
- Bachelor or Master degree in Computer Science or related engineering field.
- 5+ years of hands-on experience building distributed systems in Python, Go, or Java."""

    test_candidates = [
        ExtractedCandidate(
            title="Senior Software Engineer",
            company="Razorpay",
            location="Bengaluru, India",
            department="Engineering",
            employment_type="Full-time",
            raw_url="https://job-boards.greenhouse.io/razorpay/jobs/101",
            fingerprint="fp_blr_101",
            extra_payload={"description": desc_sample}
        ),
        ExtractedCandidate(
            title="Product Designer",
            company="Razorpay",
            location="San Francisco, CA",
            department="Design",
            employment_type="Full-time",
            raw_url="https://job-boards.greenhouse.io/razorpay/jobs/102",
            fingerprint="fp_sf_102",
            extra_payload={"description": desc_sample}
        ),
        ExtractedCandidate(
            title="DevOps Engineer",
            company="Razorpay",
            location=None,
            department="Infrastructure",
            employment_type="Full-time",
            raw_url="https://job-boards.greenhouse.io/razorpay/jobs/103",
            fingerprint="fp_unk_103",
            extra_payload={"description": desc_sample}
        )
    ]

    ingest_res = await norm_service.ingest_candidates(
        board_id="board-razorpay",
        board_run_id="run-test-001",
        extracted_candidates=test_candidates,
        family="greenhouse"
    )
    print(f"✓ Ingestion result: {ingest_res}")

    # Process pending outbox (handoff disabled)
    processed = await handoff_proc.process_pending_outbox()
    print(f"✓ Outbox process result (handoff disabled): processed={processed}")

    # Read back and verify assertions
    async with async_session_factory() as session:
        cands_res = await session.execute(select(CandidateJob))
        cands = cands_res.scalars().all()
        print(f"✓ Total CandidateJob rows persisted: {len(cands)}")
        assert len(cands) == 3

        outbox_res = await session.execute(select(HandoffOutbox))
        outbox_rows = outbox_res.scalars().all()
        print(f"✓ Total HandoffOutbox rows persisted: {len(outbox_rows)}")
        assert len(outbox_rows) == 2, f"Expected exactly 2 outbox rows (India + Missing location), got {len(outbox_rows)}"

        attempts_res = await session.execute(select(HandoffAttempt))
        attempt_rows = attempts_res.scalars().all()
        print(f"✓ Total HandoffAttempt rows: {len(attempt_rows)}")
        assert len(attempt_rows) == 0, "Zero outbound attempts must be recorded when handoff is disabled"

        for c in cands:
            outbox_entry = next((o for o in outbox_rows if o.candidate_id == c.candidate_id), None)
            if c.title == "Product Designer":
                assert c.india_eligible is False
                assert "NON_INDIA_LOCATION" in c.india_exclusion_reason
                assert outbox_entry is None, "Non-India candidate must NOT have outbox row"
                print(f"  - Non-India candidate correctly persisted & excluded: '{c.title}' ({c.location}) -> {c.india_exclusion_reason}")
            else:
                assert c.india_eligible is True
                assert outbox_entry is not None, "India-eligible candidate must have outbox row"
                print(f"  - India-eligible candidate enqueued: '{c.title}' ({c.location or 'None'}) -> outbox state: {outbox_entry.state}")

    print("\n✓ ALL ISOLATED PERSISTENCE VERIFICATION GATES PASSED CLEANLY!")
    await engine.dispose()
    if os.path.exists(temp_db_path):
        os.remove(temp_db_path)
    if os.path.exists(f"{temp_db_path}.settings.json"):
        os.remove(f"{temp_db_path}.settings.json")

if __name__ == "__main__":
    asyncio.run(verify_isolated_persistence())
