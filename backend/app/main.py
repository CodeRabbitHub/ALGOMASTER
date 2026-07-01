from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.database import engine, Base, AsyncSessionLocal
from app.api import problems, attempts, analytics, ai, admin, auth, settings as settings_api
from app.api import interview as interview_api
from app.models.user import User        # ensure User table is registered
from app.models.settings import AppSetting  # ensure app_settings table is registered
from app.models import interview as interview_models  # register interview tables with Base.metadata
from app.api.settings import load_openai_key_from_db
from app.seed.problems import seed_problems
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.limiter import limiter
from alembic.config import Config as AlembicConfig
from alembic import command as alembic_command
from sqlalchemy import text
import asyncio, logging, os
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migrations() -> None:
    """Run Alembic migrations to head. Must be called in a thread (not inside the running event loop)."""
    try:
        ini_path = os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini")
        cfg = AlembicConfig(os.path.abspath(ini_path))
        alembic_command.upgrade(cfg, "head")
        logger.info("Alembic migrations applied.")
    except Exception:
        logger.exception("Alembic migration failed — falling back to inline migrations.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting AlgoMaster backend...")

    # 1. Create base tables from SQLAlchemy models (idempotent)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. Inline safety-net for critical columns that must exist immediately.
    #    These are idempotent (IF NOT EXISTS) and run synchronously before Alembic,
    #    so the app never starts with a missing column even if Alembic is slow.
    async with engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE"
        ))
        SENTINEL = "'00000000-0000-0000-0000-000000000001'::uuid"
        await conn.execute(text(
            "ALTER TABLE problems ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]'"
        ))
        await conn.execute(text(
            "ALTER TABLE problems ADD COLUMN IF NOT EXISTS constraints TEXT DEFAULT ''"
        ))
        await conn.execute(text(
            "ALTER TABLE problems ADD COLUMN IF NOT EXISTS input_params JSONB DEFAULT '[]'"
        ))
        await conn.execute(text(
            "ALTER TABLE problems ADD COLUMN IF NOT EXISTS output_type TEXT DEFAULT ''"
        ))
        await conn.execute(text(
            "ALTER TABLE problems ADD COLUMN IF NOT EXISTS hints JSONB DEFAULT '[]'"
        ))
        # insight_type_enum was removed (L-1 fix) — column is now VARCHAR(50).
        # Wrap in DO block so existing DBs that still have the old enum don't crash.
        await conn.execute(text("""
            DO $$ BEGIN
                ALTER TYPE insight_type_enum ADD VALUE IF NOT EXISTS 'hint';
                ALTER TYPE insight_type_enum ADD VALUE IF NOT EXISTS 'mistake_explain';
            EXCEPTION WHEN undefined_object THEN NULL;
            END $$
        """))
        for tbl in ["problem_attempts", "error_patterns", "ai_insights", "learning_milestones"]:
            await conn.execute(text(
                f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS user_id UUID NOT NULL DEFAULT {SENTINEL}"
            ))
        await conn.execute(text(
            f"ALTER TABLE problem_progress ADD COLUMN IF NOT EXISTS user_id UUID NOT NULL DEFAULT {SENTINEL}"
        ))
        await conn.execute(text(
            "ALTER TABLE problem_progress DROP CONSTRAINT IF EXISTS problem_progress_pkey"
        ))
        await conn.execute(text("""
            DO $$ BEGIN
                ALTER TABLE problem_progress ADD PRIMARY KEY (problem_id, user_id);
            EXCEPTION WHEN others THEN NULL;
            END $$
        """))
        await conn.execute(text(
            f"ALTER TABLE topic_mastery ADD COLUMN IF NOT EXISTS user_id UUID NOT NULL DEFAULT {SENTINEL}"
        ))
        await conn.execute(text(
            "ALTER TABLE topic_mastery DROP CONSTRAINT IF EXISTS topic_mastery_pkey"
        ))
        await conn.execute(text("""
            DO $$ BEGIN
                ALTER TABLE topic_mastery ADD PRIMARY KEY (category, user_id);
            EXCEPTION WHEN others THEN NULL;
            END $$
        """))

    # 2b. Interview module tables (idempotent CREATE TABLE IF NOT EXISTS)
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS self_assessments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
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
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS review_schedule (
                problem_id INTEGER NOT NULL,
                user_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
                next_review_at TIMESTAMPTZ NOT NULL,
                interval_days FLOAT DEFAULT 1.0,
                ease_factor FLOAT DEFAULT 2.5,
                rep_count INTEGER DEFAULT 0,
                last_score SMALLINT,
                last_reviewed_at TIMESTAMPTZ,
                added_at TIMESTAMPTZ DEFAULT now(),
                PRIMARY KEY (problem_id, user_id)
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS mistake_log (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
                problem_id INTEGER,
                occurred_at TIMESTAMPTZ DEFAULT now(),
                category VARCHAR(100) NOT NULL,
                notes TEXT
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS contest_log (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
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
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ds_fluency (
                user_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
                ds_name VARCHAR(100) NOT NULL,
                rating SMALLINT DEFAULT 1,
                last_updated TIMESTAMPTZ DEFAULT now(),
                PRIMARY KEY (user_id, ds_name)
            )
        """))
        # Indices for common queries
        for idx_sql in [
            "CREATE INDEX IF NOT EXISTS idx_self_ass_user ON self_assessments(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_self_ass_problem ON self_assessments(problem_id)",
            "CREATE INDEX IF NOT EXISTS idx_mistake_log_user ON mistake_log(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_contest_log_user ON contest_log(user_id)",
        ]:
            await conn.execute(text(idx_sql))

    # 3. Run Alembic in a thread pool to avoid event-loop conflict
    #    (alembic's env.py uses asyncio.run() which cannot be called inside a running loop)
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as pool:
        await loop.run_in_executor(pool, run_migrations)

    await seed_problems()
    # Load encrypted OpenAI key from DB if not set via env var
    async with AsyncSessionLocal() as db:
        loaded = await load_openai_key_from_db(db)
        if loaded:
            logger.info("OpenAI API key loaded.")
        else:
            logger.warning("OpenAI API key not configured — AI features disabled. "
                           "Set it via the Settings page or add OPENAI_API_KEY to .env.")
    logger.info("Database ready.")
    yield
    # Shutdown
    await engine.dispose()

app = FastAPI(
    title="AlgoMaster API",
    description="Backend for AlgoMaster DSA Practice Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(problems.router)
app.include_router(attempts.router)
app.include_router(analytics.router)
app.include_router(ai.router)
app.include_router(admin.router)
app.include_router(settings_api.router)
app.include_router(interview_api.router)

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/")
async def root():
    return {"message": "AlgoMaster API", "docs": "/docs"}
