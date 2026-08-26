"""add_india_eligibility

Revision ID: 20260822_india_elig
Revises: 20260821_enrich_state
Create Date: 2026-08-22 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "20260822_india_elig"
down_revision = "20260821_enrich_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "candidate_jobs",
        sa.Column("india_eligible", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "candidate_jobs",
        sa.Column("india_exclusion_reason", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("candidate_jobs", "india_exclusion_reason")
    op.drop_column("candidate_jobs", "india_eligible")
