from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserOut
from app.core.security import hash_password, verify_password, create_access_token
from app.core.deps import get_current_user
from app.core.limiter import limiter
import uuid

router = APIRouter(prefix="/auth", tags=["auth"])

# Sentinel UUID — pre-auth data is tagged with this
SENTINEL_UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")

# Arbitrary fixed key for a Postgres transaction-scoped advisory lock (see
# register() below). Any 64-bit signed integer works — it just needs to be
# constant so every registration attempt contends for the same lock.
_REGISTER_LOCK_KEY = 727384001991


@router.post("/register", response_model=TokenResponse)
@limiter.limit("5/minute")
async def register(request: Request, req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Serialize registrations against each other for the rest of this
    # transaction. Without this, two concurrent first-time registrations
    # could both observe `user_count == 0` before either commits and both
    # get promoted to admin (and both independently claim the legacy
    # sentinel data). The lock is automatically released when the
    # transaction commits or rolls back at the end of the request.
    await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": _REGISTER_LOCK_KEY})

    # Check duplicates (still enforced at the DB level too — see the
    # IntegrityError handling below — since this check-then-act is not
    # itself race-free against a *different* user id doing the same email).
    existing = await db.execute(
        select(User).where((User.email == req.email) | (User.username == req.username))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email or username already taken")

    # Count existing users before adding the new one
    count_q = await db.execute(select(func.count()).select_from(User))
    user_count = count_q.scalar() or 0

    user = User(
        email=req.email,
        username=req.username,
        hashed_pw=hash_password(req.password),
    )
    db.add(user)

    try:
        await db.flush()  # get user.id assigned; also surfaces unique-constraint violations
    except IntegrityError:
        # get_db()'s dependency wrapper rolls back on any exception raised
        # here, so we don't need to (and shouldn't — the session is about
        # to be torn down by that same wrapper).
        raise HTTPException(status_code=400, detail="Email or username already taken")

    # If this is the FIRST user, make them admin and claim all legacy (sentinel) data
    if user_count == 0:
        user.is_admin = True
        await _claim_legacy_data(db, user.id)

    await db.commit()

    token = create_access_token(user.id, user.username)
    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        username=user.username,
        email=user.email,
        is_admin=user.is_admin,
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.hashed_pw):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(user.id, user.username)
    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        username=user.username,
        email=user.email,
        is_admin=user.is_admin,
    )


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return UserOut(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username,
        is_admin=current_user.is_admin,
        created_at=current_user.created_at,
    )


# Tables that carry a `user_id` column defaulting to the pre-auth sentinel
# UUID and therefore need their rows reassigned to the first real account.
# Keep this in sync with every model that uses SENTINEL_UUID as a default
# (see app/models/attempt.py, app/models/analytics.py, app/models/problem.py,
# app/models/interview.py) — it previously omitted the five interview-module
# tables entirely, silently orphaning any pre-auth interview data forever.
_LEGACY_CLAIM_TABLES = [
    "problem_progress", "problem_attempts", "error_patterns",
    "ai_insights", "learning_milestones", "topic_mastery",
    "self_assessments", "review_schedule", "mistake_log",
    "contest_log", "ds_fluency",
]


async def _claim_legacy_data(db: AsyncSession, user_id: uuid.UUID):
    """Transfer all pre-auth sentinel data to the first registered user."""
    sentinel = str(SENTINEL_UUID)
    uid = str(user_id)
    for table in _LEGACY_CLAIM_TABLES:
        await db.execute(
            text(f"UPDATE {table} SET user_id = :uid WHERE user_id = :sentinel"),
            {"uid": uid, "sentinel": sentinel},
        )
