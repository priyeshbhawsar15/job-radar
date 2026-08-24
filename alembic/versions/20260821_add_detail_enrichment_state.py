"""add_detail_enrichment_state

Revision ID: 20260821_enrich_state
Revises:
Create Date: 2026-08-21 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260821_enrich_state"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "candidate_jobs",
        sa.Column("detail_enrichment_status", sa.String(length=50), nullable=False, server_default="pending"),
    )
    op.add_column(
        "candidate_jobs",
        sa.Column("detail_enrichment_attempts", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "candidate_jobs",
        sa.Column("detail_enrichment_error_code", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "candidate_jobs",
        sa.Column("detail_enriched_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_candidate_enrichment_status",
        "candidate_jobs",
        ["detail_enrichment_status"],
        unique=False,
    )

    # Set existing rows with description to 'succeeded' or 'not_required'
    op.execute(
        "UPDATE candidate_jobs SET detail_enrichment_status = 'succeeded' WHERE description IS NOT NULL AND length(description) > 0"
    )


def downgrade() -> None:
    op.drop_index("idx_candidate_enrichment_status", table_name="candidate_jobs")
    op.drop_column("candidate_jobs", "detail_enriched_at")
    op.drop_column("candidate_jobs", "detail_enrichment_error_code")
    op.drop_column("candidate_jobs", "detail_enrichment_attempts")
    op.drop_column("candidate_jobs", "detail_enrichment_status")
