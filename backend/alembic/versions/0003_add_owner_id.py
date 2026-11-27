"""add owner_id to runs (user accounts, docs/DECISIONS.md "User accounts design")

owner_id is the Supabase user id (the token's sub claim) of the user who created the run, or NULL for a
guest run. The index on (owner_id, created_at) serves "list my runs, newest first".

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-27
"""
import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("owner_id", sa.Uuid(), nullable=True))
    op.create_index("ix_runs_owner_id_created_at", "runs", ["owner_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_runs_owner_id_created_at", table_name="runs")
    with op.batch_alter_table("runs") as batch:  # SQLite cannot drop a column in place
        batch.drop_column("owner_id")
