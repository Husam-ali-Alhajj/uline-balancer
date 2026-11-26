"""enable row level security on runs and alembic_version (PostgreSQL only)

Only the backend talks to the database (MASTER.md section 6). The backend connects as the table owner,
which bypasses row level security; Supabase's public roles (anon, authenticated) must not reach these
tables. Row level security with no policies blocks them from reading and writing rows, and the revoke
removes the privileges RLS does not cover (TRUNCATE, REFERENCES, TRIGGER), which a new Supabase project
grants by default. On SQLite (local development and tests) this migration does nothing.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-27
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

TABLES = ("runs", "alembic_version")

# The roles exist on Supabase but not on a plain PostgreSQL server, so the revoke is conditional.
REVOKE_PUBLIC_ROLES = """
DO $$
DECLARE r text;
BEGIN
    FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
            EXECUTE format('REVOKE ALL ON TABLE public.runs, public.alembic_version FROM %I', r);
        END IF;
    END LOOP;
END
$$;
"""


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in TABLES:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
    op.execute(REVOKE_PUBLIC_ROLES)


def downgrade() -> None:
    # The revoked privileges are not granted back: they were never needed.
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in TABLES:
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY")
