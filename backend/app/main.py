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
import asyncio, logging, os
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migrations() -> None:
    """
    Run Alembic migrations to head. Must be called in a thread (not inside
    the running event loop).

    This used to be paired with a large block of hand-written, idempotent
    `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` / `CREATE TABLE IF NOT
    EXISTS` statements that ran unconditionally on every single startup —
    including one migration (001) whose own docstring said it "replaces"
    that inline SQL, and a set of interview-module tables that existed in
    neither init.sql nor any Alembic migration at all. That left the schema
    with three overlapping, drifting sources of truth. Alembic (migrations
    001 and 002) is now the only one: if it fails, we let the exception
    propagate and stop the app from starting rather than silently serving
    traffic against a schema we're not sure matches the code.
    """
    ini_path = os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini")
    cfg = AlembicConfig(os.path.abspath(ini_path))
    alembic_command.upgrade(cfg, "head")
    logger.info("Alembic migrations applied.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting AlgoMaster backend...")

    # 1. Create base tables from SQLAlchemy models (idempotent). This alone
    #    is sufficient for a brand-new, empty database — every table in the
    #    current models is created with today's columns. Alembic (below) is
    #    what carries an *existing* database from an older schema forward.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. Run Alembic in a thread pool to avoid event-loop conflict
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
