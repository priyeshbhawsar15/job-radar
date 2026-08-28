from datetime import datetime
import uuid
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, Index, Text, UniqueConstraint, BigInteger, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from job_radar.db.base import Base, utc_now

if TYPE_CHECKING:
    from job_radar.db.models.board import Board
    from job_radar.db.models.run import BoardRun
    from job_radar.db.models.handoff import HandoffOutbox


class CandidateJob(Base):
    __tablename__ = "candidate_jobs"

    candidate_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    board_id: Mapped[str] = mapped_column(String(36), ForeignKey("boards.board_id", ondelete="CASCADE"), nullable=False)
    identity_key: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_url_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    public_apply_url: Mapped[str] = mapped_column(Text, nullable=False)
    posting_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    employment_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    salary_raw: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    salary_min: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    salary_max: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    salary_currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    detail_enrichment_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    detail_enrichment_attempts: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    detail_enrichment_error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    detail_enriched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    location_decision: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    location_evidence: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location_provider_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location_confidence: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    india_eligible: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    india_exclusion_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    handoff_outbox: Mapped[Optional["HandoffOutbox"]] = relationship("HandoffOutbox", back_populates="candidate", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("canonical_url_hash", "board_id", name="uq_candidate_canonical_board"),
        Index("idx_candidate_identity_key", "identity_key"),
        Index("idx_candidate_discovered", "discovered_at"),
        Index("idx_candidate_enrichment_status", "detail_enrichment_status"),
    )


class RunCandidate(Base):
    __tablename__ = "run_candidates"

    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("board_runs.board_run_id", ondelete="CASCADE"), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidate_jobs.candidate_id", ondelete="CASCADE"), primary_key=True)
    board_id: Mapped[str] = mapped_column(String(36), ForeignKey("boards.board_id", ondelete="CASCADE"), nullable=False)
    observation_outcome: Mapped[str] = mapped_column(String(50), nullable=False, default="discovered")
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    board_run: Mapped["BoardRun"] = relationship("BoardRun", back_populates="run_candidates")
    candidate: Mapped["CandidateJob"] = relationship("CandidateJob")
