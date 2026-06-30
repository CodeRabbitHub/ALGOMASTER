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
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.limiter import limiter
from alembic.config import Config as AlembicConfig
from alembic import command as alembic_command
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migrations() -> None:
    """Run Alembic migrations to head (versioned, rollback-capable)."""
    ini_path = os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini")
    cfg = AlembicConfig(os.path.abspath(ini_path))
    alembic_command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting AlgoMaster backend...")
    # Create base tables (idempotent; Alembic manages columns from here on)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Apply versioned migrations (adds/alters columns, rollback-capable)
    run_migrations()
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

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/")
async def root():
    return {"message": "AlgoMaster API", "docs": "/docs"}
