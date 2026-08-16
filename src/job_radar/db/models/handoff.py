from datetime import datetime
import uuid
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Integer, DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from job_radar.db.base import Base, utc_now

if TYPE_CHECKING:
    from job_radar.db.models.candidate import CandidateJob


class HandoffOutbox(Base):
    __tablename__ = "handoff_outbox"

    outbox_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidate_jobs.candidate_id", ondelete="CASCADE"), unique=True, nullable=False)
    contract_revision: Mapped[str] = mapped_column(String(50), nullable=False, default="v1")
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="not_eligible")  # not_eligible, queued, dispatching, accepted, held, rejected, uncertain
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    receipt_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    candidate: Mapped["CandidateJob"] = relationship("CandidateJob", back_populates="handoff_outbox")
    attempts: Mapped[List["HandoffAttempt"]] = relationship("HandoffAttempt", back_populates="outbox", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_outbox_state_retry", "state", "next_retry_at"),
    )


class HandoffAttempt(Base):
    __tablename__ = "handoff_attempts"

    attempt_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    outbox_id: Mapped[str] = mapped_column(String(36), ForeignKey("handoff_outbox.outbox_id", ondelete="CASCADE"), nullable=False)
    attempt_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    http_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    safe_outcome: Mapped[str] = mapped_column(String(50), nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    outbox: Mapped["HandoffOutbox"] = relationship("HandoffOutbox", back_populates="attempts")
