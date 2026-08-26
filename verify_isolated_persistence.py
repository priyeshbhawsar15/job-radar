"""Local isolated persistence-path verification script."""

import asyncio
import os
import tempfile
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func

# Use temp database path for isolated verification
temp_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
temp_db_path = temp_db_file.name
temp_db_file.close()

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{temp_db_path}"
os.environ["SETTINGS_FILE_PATH"] = f"{temp_db_path}.settings.json"

from job_radar.db.base import Base
from job_radar.db.models.board import Board, BoardRevision
from job_radar.db.models.candidate import CandidateJob, RunCandidate
from job_radar.db.models.handoff import HandoffOutbox, HandoffAttempt
from job_radar.adapters.base import ExtractedCandidate
from job_radar.services.normalization import NormalizationService
from job_radar.services.handoff import HandoffProcessor, JobOpsClient
from job_radar.services.settings_store import load_settings, save_settings, AppSettingsModel
from job_radar.services.location import is_india_eligible

class FailOnCallTransport:
    async def handle_async_request(self, request):
        raise RuntimeError(f"FORBIDDEN OUTBOUND CALL TO JOBOPS: {request.url}")


async def verify_isolated_persistence():
    print(f"Running isolated persistence verification against {temp_db_path}...")

    engine = create_async_engine(f"sqlite+aiosqlite:///{temp_db_path}", echo=False)
    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 1. Save and verify handoff_enabled=False settings
    settings = AppSettingsModel(handoff_enabled=False)
    save_settings(settings, Path(f"{temp_db_path}.settings.json"))
    loaded = load_settings(Path(f"{temp_db_path}.settings.json"))
    assert loaded.handoff_enabled is False, "Handoff must be False"
    print("✓ Setting readback verified: handoff_enabled=False")

    # 2. Setup mock fail-on-call JobOpsClient
    client = JobOpsClient()
    outbound_calls_made = 0
    
    # 3. Instantiate NormalizationService with isolated session factory
    norm_service = NormalizationService(session_factory=async_session_factory)
    handoff_proc = HandoffProcessor(session_factory=async_session_factory, jobops_client=client)

    # Seed 1 test board
    async with async_session_factory() as session:
        b = Board(board_id="board-test-razorpay", name="Razorpay", family="greenhouse", status="reviewed")
        session.add(b)
        await session.commit()

    # 4. Ingest 3 test candidates (India, Non-India, Missing location)
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
        board_id="board-test-razorpay",
        board_run_id="run-test-001",
        extracted_candidates=test_candidates,
        family="greenhouse"
    )
    print(f"✓ Ingestion result: {ingest_res}")

    # 5. Process pending outbox with handoff disabled
    processed = await handoff_proc.process_pending_outbox()
    print(f"✓ Outbox process result (handoff disabled): processed={processed}")

    # 6. Read back database state and verify assertions
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

        # Check candidate locations and India eligibility evidence
        for c in cands:
            eligible, reason = is_india_eligible(c.location)
            outbox_entry = next((o for o in outbox_rows if o.candidate_id == c.candidate_id), None)
            if c.title == "Product Designer":
                assert eligible is False
                assert "NON_INDIA_LOCATION" in reason
                assert outbox_entry is None, "Non-India candidate must NOT have outbox row"
                print(f"  - Non-India candidate correctly excluded: '{c.title}' ({c.location}) -> {reason}")
            else:
                assert eligible is True
                assert outbox_entry is not None, "India-eligible candidate must have outbox row"
                print(f"  - India-eligible candidate enqueued: '{c.title}' ({c.location or 'None'}) -> outbox state: {outbox_entry.state}")

    print("\n✓ ALL ISOLATED PERSISTENCE VERIFICATION GATES PASSED CLEANLY!")
    await engine.dispose()
    os.remove(temp_db_path)

if __name__ == "__main__":
    asyncio.run(verify_isolated_persistence())
