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
