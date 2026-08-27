"""make candidate identity keys non-unique

Revision ID: 20260828_url_dedup
Revises: 20260827_loc_decision
Create Date: 2026-08-28 00:00:00.000000

A semantic identity key is audit metadata, not a candidate identity.  Candidate
re-observation is exclusively the board-scoped canonical URL constraint.
"""
from alembic import op
import sqlalchemy as sa

revision = "20260828_url_dedup"
down_revision = "20260827_loc_decision"
branch_labels = None
depends_on = None


def _sqlite_candidate_table_without_identity_unique() -> sa.Table:
    """Reflect candidate_jobs and remove only its identity-key uniqueness."""
    bind = op.get_bind()
    metadata = sa.MetaData()
    table = sa.Table("candidate_jobs", metadata, autoload_with=bind)

    for constraint in list(table.constraints):
        if isinstance(constraint, sa.UniqueConstraint) and list(constraint.columns.keys()) == ["identity_key"]:
            table.constraints.remove(constraint)
    for index in list(table.indexes):
        if index.unique and list(index.columns.keys()) == ["identity_key"]:
            table.indexes.remove(index)
    return table


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        # SQLite cannot drop an anonymous UNIQUE constraint in place. Batch
        # recreation preserves data, named URL uniqueness, and foreign keys.
        with op.batch_alter_table(
            "candidate_jobs",
            recreate="always",
            copy_from=_sqlite_candidate_table_without_identity_unique(),
        ):
            pass
    else:
        inspector = sa.inspect(bind)
        for constraint in inspector.get_unique_constraints("candidate_jobs"):
            if constraint.get("column_names") == ["identity_key"]:
                name = constraint.get("name")
                if name:
                    op.drop_constraint(name, "candidate_jobs", type_="unique")
        for index in inspector.get_indexes("candidate_jobs"):
            if index.get("unique") and index.get("column_names") == ["identity_key"]:
                op.drop_index(index["name"], table_name="candidate_jobs")

    op.create_index("idx_candidate_identity_key", "candidate_jobs", ["identity_key"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    duplicates = bind.execute(
        sa.text(
            "SELECT identity_key FROM candidate_jobs "
            "GROUP BY identity_key HAVING COUNT(*) > 1 LIMIT 1"
        )
    ).first()
    if duplicates:
        raise RuntimeError(
            "Cannot downgrade 20260828_url_dedup: candidate_jobs contains "
            "duplicate identity_key values; refusing lossy restoration of the "
            "former unique constraint."
        )

    if bind.dialect.name == "sqlite":
        table = sa.Table("candidate_jobs", sa.MetaData(), autoload_with=bind)
        with op.batch_alter_table("candidate_jobs", recreate="always", copy_from=table) as batch_op:
            batch_op.drop_index("idx_candidate_identity_key")
            batch_op.create_unique_constraint("uq_candidate_identity_key", ["identity_key"])
    else:
        op.drop_index("idx_candidate_identity_key", table_name="candidate_jobs")
        op.create_unique_constraint("uq_candidate_identity_key", "candidate_jobs", ["identity_key"])
