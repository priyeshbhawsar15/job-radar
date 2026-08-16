import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from job_radar.db.base import Base
from job_radar.db.models.board import Board
from job_radar.db.models.candidate import CandidateJob
from job_radar.db.models.run import PipelineRun, BoardRun
from job_radar.adapters.base import ExtractedCandidate
from job_radar.services.normalization import NormalizationService, RetentionPurger

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def test_session_factory():
  engine = create_async_engine(TEST_DB_URL, echo=False)
  async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)

  session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
  yield session_factory
  await engine.dispose()

@pytest.mark.asyncio
async def test_deduplication_and_normalization(test_session_factory):
  norm_svc = NormalizationService(session_factory=test_session_factory)

  # Setup board and board run
  async with test_session_factory() as session:
    board = Board(board_id="board-01", name="Stripe", family="greenhouse", status="active")
    p_run = PipelineRun(pipeline_id="p-01", trigger="manual", status="running")
    b_run = BoardRun(board_run_id="br-01", pipeline_id="p-01", board_id="board-01", stage="running", outcome="in_progress")
    session.add(board)
    session.add(p_run)
    session.add(b_run)
    await session.commit()

  candidates = [
    ExtractedCandidate(
      title="Backend Engineer",
      company="Stripe",
      location="San Francisco, CA",
      raw_url="https://boards.greenhouse.io/stripe/jobs/1",
      fingerprint="fp_test_1"
    ),
    ExtractedCandidate(
      title="Backend Engineer",
      company="Stripe",
      location="San Francisco, CA",
      raw_url="https://boards.greenhouse.io/stripe/jobs/1",
      fingerprint="fp_test_1"
    )
  ]

  total, new_created = await norm_svc.ingest_candidates("board-01", "br-01", candidates)
  assert total == 2
  assert new_created == 1  # 2nd item deduplicated by identity_key!

@pytest.mark.asyncio
async def test_7day_retention_purger(test_session_factory):
  purger = RetentionPurger(retention_days=7, session_factory=test_session_factory)

  async with test_session_factory() as session:
    old_time = datetime.now(timezone.utc) - timedelta(days=10)
    old_run = PipelineRun(
      pipeline_id="old-pipeline-01",
      trigger="manual",
      status="completed",
      started_at=old_time
    )
    session.add(old_run)
    await session.commit()

  counts = await purger.purge_expired_records()
  assert counts["pipeline_runs"] == 1
