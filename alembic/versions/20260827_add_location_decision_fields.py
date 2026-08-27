"""add_location_decision_fields

Revision ID: 20260827_loc_decision
Revises: 20260822_india_elig
Create Date: 2026-08-27 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "20260827_loc_decision"
down_revision = "20260822_india_elig"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "candidate_jobs",
        sa.Column("location_decision", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "candidate_jobs",
        sa.Column("location_evidence", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "candidate_jobs",
        sa.Column("location_confidence", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("candidate_jobs", "location_confidence")
    op.drop_column("candidate_jobs", "location_evidence")
    op.drop_column("candidate_jobs", "location_decision")
