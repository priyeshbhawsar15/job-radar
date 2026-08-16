from datetime import datetime
import uuid
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Integer, BigInteger, DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from job_radar.db.base import Base, utc_now

if TYPE_CHECKING:
    from job_radar.db.models.board import Board, BoardRevision
    from job_radar.db.models.candidate import RunCandidate


class RunRequest(Base):
    __tablename__ = "run_requests"

    request_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    board_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("boards.board_id", ondelete="SET NULL"), nullable=True)
    origin: Mapped[str] = mapped_column(String(50), nullable=False)  # scheduled, manual
    scheduled_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="requested")  # requested, admitted, held, completed, expired
    requested_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    execution_attempts: Mapped[List["ExecutionAttempt"]] = relationship("ExecutionAttempt", back_populates="request", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_requests_status_time", "status", "scheduled_time"),
    )


class ExecutionAttempt(Base):
    __tablename__ = "execution_attempts"

    execution_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id: Mapped[str] = mapped_column(String(36), ForeignKey("run_requests.request_id", ondelete="CASCADE"), nullable=False)
    fence_generation: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False)
    lease_token: Mapped[str] = mapped_column(String(36), default=lambda: str(uuid.uuid4()), nullable=False)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    stage: Mapped[str] = mapped_column(String(50), nullable=False, default="admitted")
    outcome: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    terminal_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    request: Mapped["RunRequest"] = relationship("RunRequest", back_populates="execution_attempts")

    __table_args__ = (
        Index("idx_execution_lease", "execution_id", "fence_generation"),
        Index("idx_execution_terminal", "terminal_at"),
    )


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    pipeline_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    trigger: Mapped[str] = mapped_column(String(50), nullable=False)  # scheduled, manual
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="running")  # running, completed, partial, failed, cancelled
    total_boards: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    extracted_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    accepted_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    held_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    terminal_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    board_runs: Mapped[List["BoardRun"]] = relationship("BoardRun", back_populates="pipeline_run", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_pipeline_terminal", "terminal_at"),
    )


class BoardRun(Base):
    __tablename__ = "board_runs"

    board_run_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipeline_runs.pipeline_id", ondelete="CASCADE"), nullable=False)
    board_id: Mapped[str] = mapped_column(String(36), ForeignKey("boards.board_id", ondelete="CASCADE"), nullable=False)
    revision_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("board_revisions.revision_id", ondelete="SET NULL"), nullable=True)
    stage: Mapped[str] = mapped_column(String(50), nullable=False, default="completed")
    outcome: Mapped[str] = mapped_column(String(50), nullable=False)  # success, empty_verified, partial, challenge, timeout, parser_contract, provider_failure
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    extracted_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    terminal_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    pipeline_run: Mapped["PipelineRun"] = relationship("PipelineRun", back_populates="board_runs")
    run_candidates: Mapped[List["RunCandidate"]] = relationship("RunCandidate", back_populates="board_run", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_board_runs_terminal", "terminal_at"),
    )
