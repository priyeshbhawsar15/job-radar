"""persist bounded provider location evidence

Revision ID: 20260828_provider_geo
Revises: 20260828_url_dedup
"""
from alembic import op
import sqlalchemy as sa

revision = "20260828_provider_geo"
down_revision = "20260828_url_dedup"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("candidate_jobs", sa.Column("location_provider_evidence", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("candidate_jobs", "location_provider_evidence")
