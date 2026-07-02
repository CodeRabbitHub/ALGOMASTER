"""Initial column migrations (replaces inline ALTER TABLE in lifespan)

Revision ID: 001
Revises:
Create Date: 2026-01-01 00:00:00.000000

Note on insight_type_enum: this type doesn't exist on a fresh database (or
any install seeded from db/init.sql — ai_insights.insight_type has always
been a plain VARCHAR there, not an enum), so an un-guarded
`ALTER TYPE insight_type_enum ADD VALUE ...` would abort the whole
migration with "type does not exist". We check for the type first with a
plain query and only run the ALTER TYPE if it's actually present.
(`ALTER TYPE ... ADD VALUE` also cannot be run from inside a PL/pgSQL
DO block/function — Postgres rejects that outright — so the check has to
happen as a separate, preceding statement rather than as an exception
handler wrapped around it.)
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SENTINEL = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    # ── problems table column additions ──────────────────────────────────────
    op.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]'")
    op.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS constraints TEXT DEFAULT ''")
    op.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS input_params JSONB DEFAULT '[]'")
    op.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS output_type TEXT DEFAULT ''")
    op.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS hints JSONB DEFAULT '[]'")

    # ── insight_type enum additions (only if the legacy enum type exists) ─────
    bind = op.get_bind()
    enum_exists = bind.execute(sa.text(
        "SELECT 1 FROM pg_type WHERE typname = 'insight_type_enum'"
    )).scalar()
    if enum_exists:
        op.execute("ALTER TYPE insight_type_enum ADD VALUE IF NOT EXISTS 'hint'")
        op.execute("ALTER TYPE insight_type_enum ADD VALUE IF NOT EXISTS 'mistake_explain'")

    # ── Auth / multi-user column additions ───────────────────────────────────
    sentinel = f"'{SENTINEL}'::uuid"
    for tbl in ["problem_attempts", "error_patterns", "ai_insights", "learning_milestones"]:
        op.execute(
            f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS user_id UUID NOT NULL DEFAULT {sentinel}"
        )

    # problem_progress composite PK (problem_id, user_id)
    op.execute(
        f"ALTER TABLE problem_progress ADD COLUMN IF NOT EXISTS user_id UUID NOT NULL DEFAULT {sentinel}"
    )
    op.execute("ALTER TABLE problem_progress DROP CONSTRAINT IF EXISTS problem_progress_pkey")
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE problem_progress ADD PRIMARY KEY (problem_id, user_id);
        EXCEPTION WHEN others THEN NULL;
        END $$
    """)

    # topic_mastery composite PK (category, user_id)
    op.execute(
        f"ALTER TABLE topic_mastery ADD COLUMN IF NOT EXISTS user_id UUID NOT NULL DEFAULT {sentinel}"
    )
    op.execute("ALTER TABLE topic_mastery DROP CONSTRAINT IF EXISTS topic_mastery_pkey")
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE topic_mastery ADD PRIMARY KEY (category, user_id);
        EXCEPTION WHEN others THEN NULL;
        END $$
    """)

    # ── Admin role column ─────────────────────────────────────────────────────
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE")


def downgrade() -> None:
    # Column removals (order matters for constraints)
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS is_admin")

    op.execute("ALTER TABLE topic_mastery DROP CONSTRAINT IF EXISTS topic_mastery_pkey")
    op.execute("ALTER TABLE topic_mastery DROP COLUMN IF EXISTS user_id")

    op.execute("ALTER TABLE problem_progress DROP CONSTRAINT IF EXISTS problem_progress_pkey")
    op.execute("ALTER TABLE problem_progress DROP COLUMN IF EXISTS user_id")

    for tbl in ["learning_milestones", "ai_insights", "error_patterns", "problem_attempts"]:
        op.execute(f"ALTER TABLE {tbl} DROP COLUMN IF EXISTS user_id")

    op.execute("ALTER TABLE problems DROP COLUMN IF EXISTS hints")
    op.execute("ALTER TABLE problems DROP COLUMN IF EXISTS output_type")
    op.execute("ALTER TABLE problems DROP COLUMN IF EXISTS input_params")
    op.execute("ALTER TABLE problems DROP COLUMN IF EXISTS constraints")
    op.execute("ALTER TABLE problems DROP COLUMN IF EXISTS tags")
