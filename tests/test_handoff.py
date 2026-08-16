import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from job_radar.db.base import Base
from job_radar.db.models.board import Board
from job_radar.db.models.candidate import CandidateJob
from job_radar.db.models.handoff import HandoffOutbox, HandoffAttempt
from job_radar.services.handoff import HandoffProcessor, JobOpsClient

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
async def test_transactional_outbox_processing(test_session_factory):
  mock_client = JobOpsClient(endpoint="http://mock-jobops.local/api")

  processor = HandoffProcessor(session_factory=test_session_factory, jobops_client=mock_client)

  # Setup board & candidate in DB
  async with test_session_factory() as session:
    board = Board(board_id="board-01", name="Stripe", family="greenhouse", status="active")
    cand = CandidateJob(
      candidate_id="cand-01",
      board_id="board-01",
      identity_key="id_01",
      canonical_url_hash="hash_01",
      title="Senior Engineer",
      company="Stripe",
      public_apply_url="https://stripe.com/jobs/1"
    )
    session.add(board)
    session.add(cand)
    await session.commit()

  # Enqueue outbox item
  outbox = await processor.enqueue_candidate_handoff(
    candidate_id="cand-01",
    payload_json={"title": "Senior Engineer", "company": "Stripe"}
  )
  assert outbox.state == "queued"

  # Force settings handoff enabled
  with patch("job_radar.services.handoff.settings.HANDOFF_ENABLED", True), \
       patch.object(mock_client, "push_candidate", new_callable=AsyncMock) as mock_push:

    mock_push.return_value = True

    processed = await processor.process_pending_outbox()
    assert processed == 1

  # Verify status updated to accepted
  async with test_session_factory() as session:
    res = await session.execute(select(HandoffOutbox).where(HandoffOutbox.outbox_id == outbox.outbox_id))
    rec = res.scalar_one()
    assert rec.state == "accepted"
