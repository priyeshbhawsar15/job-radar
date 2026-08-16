import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from job_radar.db.session import AsyncSessionLocal
from job_radar.db.models.board import Board, BoardRevision
from job_radar.db.models.run import PipelineRun, BoardRun, RunRequest, ExecutionAttempt
from job_radar.adapters.registry import adapter_registry
from job_radar.services.browser import BrowserServiceClient, TargetBoundaryViolation

logger = logging.getLogger(__name__)

class PipelineExecutionEngine:
  """Stateful engine for executing board parsing runs with retry & threshold rules."""

  def __init__(self, session_factory=AsyncSessionLocal):
    self.session_factory = session_factory
    self.browser_client = BrowserServiceClient()

  async def execute_board_run(
    self,
    board_id: str,
    pipeline_id: Optional[str] = None
  ) -> BoardRun:
    """Execute a single board parsing run with state transition rules."""
    async with self.session_factory() as session:
      # 1. Fetch Board and current revision
      result = await session.execute(
        select(Board).where(Board.board_id == board_id)
      )
      board = result.scalar_one_or_none()
      if not board:
        raise ValueError(f"Board not found: {board_id}")

      # If pipeline_id not supplied, create a parent PipelineRun
      if not pipeline_id:
        pipeline = PipelineRun(
          trigger="manual",
          status="running",
          total_boards=1
        )
        session.add(pipeline)
        await session.commit()
        await session.refresh(pipeline)
        pipeline_id = pipeline.pipeline_id

      if board.status == "held":
        logger.warning(f"Board {board_id} is HELD due to consecutive failures. Skipping run.")
        board_run = BoardRun(
          board_id=board_id,
          pipeline_id=pipeline_id,
          stage="completed",
          outcome="held",
          error_code="BOARD_HELD",
          terminal_at=datetime.now(timezone.utc)
        )
        session.add(board_run)
        await session.commit()
        return board_run

      revision = None
      if board.current_revision_id:
        rev_res = await session.execute(
          select(BoardRevision).where(BoardRevision.revision_id == board.current_revision_id)
        )
        revision = rev_res.scalar_one_or_none()

      target_url = "https://localhost"
      selector_config = None
      family = board.family

      if revision and isinstance(revision.config_json, dict):
        target_url = revision.config_json.get("target_url", target_url)
        selector_config = revision.config_json.get("selector_config")
        family = revision.config_json.get("family", family)

      # 2. Create BoardRun DB record
      board_run = BoardRun(
        board_id=board_id,
        pipeline_id=pipeline_id,
        revision_id=revision.revision_id if revision else None,
        stage="running",
        outcome="in_progress"
      )
      session.add(board_run)
      await session.commit()
      await session.refresh(board_run)

      # Create RunRequest & ExecutionAttempt
      run_req = RunRequest(
        board_id=board_id,
        origin="manual",
        status="admitted"
      )
      session.add(run_req)
      await session.commit()
      await session.refresh(run_req)

      # Determine parser adapter
      adapter = adapter_registry.get(family)
      if not adapter:
        board_run.stage = "completed"
        board_run.outcome = "parser_contract"
        board_run.error_code = f"UNSUPPORTED_ADAPTER_{family}"
        board_run.terminal_at = datetime.now(timezone.utc)
        board.consecutive_parser_failures += 1
        if board.consecutive_parser_failures >= 3:
          board.status = "held"
        await session.commit()
        return board_run

      # 3. Attempt Execution Loop (max 2 attempts per run)
      max_attempts = 2
      raw_payload: Optional[str] = None
      run_success = False
      error_msg: Optional[str] = None

      for attempt_num in range(1, max_attempts + 1):
        attempt_rec = ExecutionAttempt(
          request_id=run_req.request_id,
          stage="running"
        )
        session.add(attempt_rec)
        await session.commit()

        try:
          # Fetch content via browser service boundary
          raw_payload = await self.browser_client.fetch_board_html(
            target_url=target_url,
            registered_target_url=target_url
          )
          # Parse candidates
          candidates = adapter.parse_raw_payload(
            payload=raw_payload,
            board_name=board.name,
            target_url=target_url,
            selector_config=selector_config
          )

          # Successful attempt
          attempt_rec.stage = "completed"
          attempt_rec.outcome = "success"
          attempt_rec.terminal_at = datetime.now(timezone.utc)
          board_run.extracted_count = len(candidates)
          run_success = True
          await session.commit()
          break

        except TargetBoundaryViolation as tbv:
          attempt_rec.stage = "completed"
          attempt_rec.outcome = "boundary_violation"
          attempt_rec.terminal_at = datetime.now(timezone.utc)
          error_msg = str(tbv)
          await session.commit()
          break  # Don't retry boundary violations

        except Exception as e:
          attempt_rec.stage = "completed"
          attempt_rec.outcome = "error"
          attempt_rec.terminal_at = datetime.now(timezone.utc)
          error_msg = str(e)
          await session.commit()
          if attempt_num < max_attempts:
            await asyncio.sleep(1.0)  # Brief backoff

      # 4. Finalize Board Run Status and Board consecutive failures count
      board_run.terminal_at = datetime.now(timezone.utc)
      board_run.stage = "completed"
      if run_success:
        board_run.outcome = "success"
        board.consecutive_parser_failures = 0  # Reset consecutive failure counter
      else:
        board_run.outcome = "provider_failure"
        board_run.error_code = error_msg
        board.consecutive_parser_failures += 1
        if board.consecutive_parser_failures >= 3:
          board.status = "held"
          logger.warning(f"Board {board_id} exceeded failure threshold (3). Status set to HELD.")

      await session.commit()
      return board_run

execution_engine = PipelineExecutionEngine()
