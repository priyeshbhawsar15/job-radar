"""Expand BoardRun error_code length

Revision ID: 20260831_errorcode
Revises: 20260828_provider_geo
Create Date: 2026-08-31 13:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "20260831_errorcode"
down_revision: Union[str, None] = "20260828_provider_geo"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("board_runs", schema=None) as batch_op:
        batch_op.alter_column(
            "error_code",
            existing_type=sa.String(length=100),
            type_=sa.String(length=255),
            existing_nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("board_runs", schema=None) as batch_op:
        batch_op.alter_column(
            "error_code",
            existing_type=sa.String(length=255),
            type_=sa.String(length=100),
            existing_nullable=True,
        )
