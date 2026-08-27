import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from job_radar.db.models.board import Board
from job_radar.db.models.candidate import CandidateJob, RunCandidate
from job_radar.db.models.run import BoardRun, PipelineRun


async def _make_board(db_session: AsyncSession) -> Board:
    board = Board(name="Acme", family="generic", status="enabled")
    db_session.add(board)
    await db_session.commit()
    return board


async def _make_pipeline_run(db_session: AsyncSession) -> PipelineRun:
    pipeline_run = PipelineRun(trigger="manual", status="completed")
    db_session.add(pipeline_run)
    await db_session.commit()
    return pipeline_run


async def _make_board_run(db_session: AsyncSession, board: Board, pipeline_run: PipelineRun) -> BoardRun:
    board_run = BoardRun(
        pipeline_id=pipeline_run.pipeline_id,
        board_id=board.board_id,
        outcome="success",
    )
    db_session.add(board_run)
    await db_session.commit()
    return board_run


async def _make_candidate(db_session: AsyncSession, board: Board, **overrides) -> CandidateJob:
    defaults = dict(
        board_id=board.board_id,
        identity_key=f"acme:job:{overrides.get('canonical_url_hash', 'x')}",
        canonical_url_hash=overrides.get("canonical_url_hash", "hash-1"),
        title="Software Engineer",
        company="Acme",
        public_apply_url="https://acme.example.com/jobs/1",
    )
    defaults.update(overrides)
    candidate = CandidateJob(**defaults)
    db_session.add(candidate)
    await db_session.commit()
    return candidate


@pytest.mark.asyncio
async def test_board_run_detail_includes_observation_outcome(client: AsyncClient, db_session: AsyncSession):
    board = await _make_board(db_session)
    pipeline_run = await _make_pipeline_run(db_session)
    board_run = await _make_board_run(db_session, board, pipeline_run)

    discovered_candidate = await _make_candidate(db_session, board, canonical_url_hash="hash-discovered")
    re_observed_candidate = await _make_candidate(db_session, board, canonical_url_hash="hash-reobserved")

    db_session.add(RunCandidate(
        run_id=board_run.board_run_id,
        candidate_id=discovered_candidate.candidate_id,
        board_id=board.board_id,
        observation_outcome="discovered",
    ))
    db_session.add(RunCandidate(
        run_id=board_run.board_run_id,
        candidate_id=re_observed_candidate.candidate_id,
        board_id=board.board_id,
        observation_outcome="re_observed",
    ))
    await db_session.commit()

    resp = await client.get(f"/api/v1/runs/board-runs/{board_run.board_run_id}")

    assert resp.status_code == 200
    data = resp.json()

    assert data["board_run"]["new_discovered_count"] == 1
    assert data["board_run"]["re_observed_count"] == 1

    outcomes_by_candidate = {
        job["candidate_id"]: job["observation_outcome"] for job in data["extracted_jobs"]
    }
    assert outcomes_by_candidate[discovered_candidate.candidate_id] == "discovered"
    assert outcomes_by_candidate[re_observed_candidate.candidate_id] == "re_observed"


@pytest.mark.asyncio
async def test_list_runs_returns_grouped_enrichment_metrics_and_excludes_pending_denominator(
    client: AsyncClient, db_session: AsyncSession
):
    board = await _make_board(db_session)
    pipeline_run = await _make_pipeline_run(db_session)

    run1 = await _make_board_run(db_session, board, pipeline_run)
    run1.outcome = "partial"
    run2 = await _make_board_run(db_session, board, pipeline_run)
    run2.outcome = "success"
    await db_session.commit()

    cand1 = await _make_candidate(
        db_session, board, canonical_url_hash="hash-e1", detail_enrichment_status="succeeded"
    )
    cand2 = await _make_candidate(
        db_session, board, canonical_url_hash="hash-e2", detail_enrichment_status="failed"
    )
    cand3 = await _make_candidate(
        db_session, board, canonical_url_hash="hash-e3", detail_enrichment_status="pending"
    )
    cand4 = await _make_candidate(
        db_session, board, canonical_url_hash="hash-e4", detail_enrichment_status="succeeded"
    )

    db_session.add(RunCandidate(run_id=run1.board_run_id, candidate_id=cand1.candidate_id, board_id=board.board_id))
    db_session.add(RunCandidate(run_id=run1.board_run_id, candidate_id=cand2.candidate_id, board_id=board.board_id))
    db_session.add(RunCandidate(run_id=run1.board_run_id, candidate_id=cand3.candidate_id, board_id=board.board_id))

    db_session.add(RunCandidate(run_id=run2.board_run_id, candidate_id=cand4.candidate_id, board_id=board.board_id))
    await db_session.commit()

    resp = await client.get("/api/v1/runs")
    assert resp.status_code == 200
    runs = resp.json()

    run1_data = next(r for r in runs if r["run_id"] == run1.board_run_id)
    run2_data = next(r for r in runs if r["run_id"] == run2.board_run_id)

    assert run1_data["enrichment_succeeded"] == 1
    assert run1_data["enrichment_failed"] == 1
    assert run1_data["enrichment_total"] == 2

    assert run2_data["enrichment_succeeded"] == 1
    assert run2_data["enrichment_failed"] == 0
    assert run2_data["enrichment_total"] == 1


@pytest.mark.asyncio
async def test_board_run_detail_serializes_india_eligibility_and_reason(
    client: AsyncClient, db_session: AsyncSession
):
    board = await _make_board(db_session)
    pipeline_run = await _make_pipeline_run(db_session)
    board_run = await _make_board_run(db_session, board, pipeline_run)

    c_true = await _make_candidate(
        db_session,
        board,
        canonical_url_hash="hash-in-true",
        india_eligible=True,
        india_exclusion_reason=None,
    )
    c_false = await _make_candidate(
        db_session,
        board,
        canonical_url_hash="hash-in-false",
        india_eligible=False,
        india_exclusion_reason="Exclusively US location specified",
    )
    c_null = await _make_candidate(
        db_session,
        board,
        canonical_url_hash="hash-in-null",
        india_eligible=None,
        india_exclusion_reason=None,
    )

    db_session.add(RunCandidate(run_id=board_run.board_run_id, candidate_id=c_true.candidate_id, board_id=board.board_id))
    db_session.add(RunCandidate(run_id=board_run.board_run_id, candidate_id=c_false.candidate_id, board_id=board.board_id))
    db_session.add(RunCandidate(run_id=board_run.board_run_id, candidate_id=c_null.candidate_id, board_id=board.board_id))
    await db_session.commit()

    resp = await client.get(f"/api/v1/runs/board-runs/{board_run.board_run_id}")
    assert resp.status_code == 200
    data = resp.json()

    jobs_by_id = {j["candidate_id"]: j for j in data["extracted_jobs"]}
    assert jobs_by_id[c_true.candidate_id]["india_eligible"] is True
    assert jobs_by_id[c_true.candidate_id]["india_exclusion_reason"] is None

    assert jobs_by_id[c_false.candidate_id]["india_eligible"] is False
    assert jobs_by_id[c_false.candidate_id]["india_exclusion_reason"] == "Exclusively US location specified"

    assert jobs_by_id[c_null.candidate_id]["india_eligible"] is None
    assert jobs_by_id[c_null.candidate_id]["india_exclusion_reason"] is None
