from datetime import datetime, timezone
import uuid
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Integer, DateTime, ForeignKey, UniqueConstraint, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from job_radar.db.base import Base, utc_now

if TYPE_CHECKING:
    from job_radar.db.models.run import RunRequest, BoardRun
    from job_radar.db.models.candidate import CandidateJob, RunCandidate


class Board(Base):
    __tablename__ = "boards"

    board_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    family: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")  # draft, reviewed, enabled, paused, retired
    current_revision_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("board_revisions.revision_id", use_alter=True, name="fk_boards_current_revision_id"), nullable=True)
    consecutive_parser_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    revisions: Mapped[List["BoardRevision"]] = relationship("BoardRevision", foreign_keys="BoardRevision.board_id", back_populates="board", cascade="all, delete-orphan")
    current_revision: Mapped[Optional["BoardRevision"]] = relationship("BoardRevision", foreign_keys=[current_revision_id], post_update=True)

    __table_args__ = (
        Index("idx_boards_status", "status"),
    )


class BoardRevision(Base):
    __tablename__ = "board_revisions"

    revision_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    board_id: Mapped[str] = mapped_column(String(36), ForeignKey("boards.board_id", ondelete="CASCADE"), nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")  # draft, reviewed, rejected, superseded
    config_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    approved_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    board: Mapped["Board"] = relationship("Board", foreign_keys=[board_id], back_populates="revisions")

    __table_args__ = (
        UniqueConstraint("board_id", "revision_number", name="uq_board_revision_number"),
    )
