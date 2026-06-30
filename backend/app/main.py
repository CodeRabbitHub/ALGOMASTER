from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.database import engine, Base, AsyncSessionLocal
from app.api import problems, attempts, analytics, ai, admin, auth, settings as settings_api
from app.models.user import User        # ensure User table is registered
from app.models.settings import AppSetting  # ensure app_settings table is registered
from app.api.settings import load_openai_key_from_db
from app.seed.problems import seed_problems
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting AlgoMaster backend...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Safe migrations — adds new columns to existing DBs without data loss
        # (asyncpg requires one statement per execute call)
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
        # ── Enum migrations (safe — ADD VALUE IF NOT EXISTS is idempotent) ─────
        await conn.execute(text(
            "ALTER TYPE insight_type_enum ADD VALUE IF NOT EXISTS 'hint'"
        ))
        await conn.execute(text(
            "ALTER TYPE insight_type_enum ADD VALUE IF NOT EXISTS 'mistake_explain'"
        ))
        # ── Auth / multi-user migrations ─────────────────────────────────────
        SENTINEL = "'00000000-0000-0000-0000-000000000001'::uuid"
        for tbl in ["problem_attempts", "error_patterns", "ai_insights", "learning_milestones"]:
            await conn.execute(text(
                f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS user_id UUID NOT NULL DEFAULT {SENTINEL}"
            ))
        # problem_progress: composite PK (problem_id, user_id)
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
        # topic_mastery: composite PK (category, user_id)
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

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/")
async def root():
    return {"message": "AlgoMaster API", "docs": "/docs"}
