"""Interview readiness module tables

Adds self_assessments, review_schedule, mistake_log, contest_log, and
ds_fluency — previously created ad hoc via raw CREATE TABLE IF NOT EXISTS
statements inside app/main.py's startup lifespan on every single app boot,
alongside (and duplicating the intent of) this Alembic migration chain.
That inline DDL has been removed from main.py; this migration is now the
single source of truth for these tables, consistent with 001.

Revision ID: 002
Revises: 001
Create Date: 2026-07-02 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SENTINEL = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS self_assessments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL DEFAULT '{SENTINEL}',
            problem_id INTEGER NOT NULL,
            assessed_at TIMESTAMPTZ DEFAULT now(),
            pattern_identified VARCHAR(100),
            time_to_pattern_secs INTEGER,
            pattern_was_correct BOOLEAN,
            time_to_first_idea_secs INTEGER,
            time_to_algorithm_secs INTEGER,
            total_solve_time_secs INTEGER,
            wrong_approaches SMALLINT DEFAULT 0,
            hint_used BOOLEAN DEFAULT FALSE,
            did_panic BOOLEAN DEFAULT FALSE,
            complexity_initial_time VARCHAR(30),
            complexity_final_time VARCHAR(30),
            complexity_final_space VARCHAR(30),
            compile_attempts SMALLINT DEFAULT 1,
            bugs_count SMALLINT DEFAULT 0,
            bug_categories JSONB DEFAULT '[]',
            debug_time_secs INTEGER,
            communication_score SMALLINT,
            edge_cases_checked JSONB DEFAULT '[]',
            edge_cases_before_coding BOOLEAN,
            new_learning TEXT,
            confidence_after SMALLINT
        )
    """)
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS review_schedule (
            problem_id INTEGER NOT NULL,
            user_id UUID NOT NULL DEFAULT '{SENTINEL}',
            next_review_at TIMESTAMPTZ NOT NULL,
            interval_days FLOAT DEFAULT 1.0,
            ease_factor FLOAT DEFAULT 2.5,
            rep_count INTEGER DEFAULT 0,
            last_score SMALLINT,
            last_reviewed_at TIMESTAMPTZ,
            added_at TIMESTAMPTZ DEFAULT now(),
            PRIMARY KEY (problem_id, user_id)
        )
    """)
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS mistake_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL DEFAULT '{SENTINEL}',
            problem_id INTEGER,
            occurred_at TIMESTAMPTZ DEFAULT now(),
            category VARCHAR(100) NOT NULL,
            notes TEXT
        )
    """)
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS contest_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL DEFAULT '{SENTINEL}',
            platform VARCHAR(50) DEFAULT 'LeetCode',
            contest_name VARCHAR(200),
            contest_date TIMESTAMPTZ NOT NULL,
            rating INTEGER,
            rating_change INTEGER,
            global_rank INTEGER,
            questions_solved SMALLINT DEFAULT 0,
            total_questions SMALLINT DEFAULT 4,
            penalty_mins INTEGER,
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS ds_fluency (
            user_id UUID NOT NULL DEFAULT '{SENTINEL}',
            ds_name VARCHAR(100) NOT NULL,
            rating SMALLINT DEFAULT 1,
            last_updated TIMESTAMPTZ DEFAULT now(),
            PRIMARY KEY (user_id, ds_name)
        )
    """)

    for idx_sql in [
        "CREATE INDEX IF NOT EXISTS idx_self_ass_user ON self_assessments(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_self_ass_problem ON self_assessments(problem_id)",
        "CREATE INDEX IF NOT EXISTS idx_mistake_log_user ON mistake_log(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_contest_log_user ON contest_log(user_id)",
    ]:
        op.execute(idx_sql)


def downgrade() -> None:
    for table in ["ds_fluency", "contest_log", "mistake_log", "review_schedule", "self_assessments"]:
        op.execute(f"DROP TABLE IF EXISTS {table}")
