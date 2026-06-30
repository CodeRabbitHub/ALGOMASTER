from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.database import get_db
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserOut
from app.core.security import hash_password, verify_password, create_access_token
from app.core.deps import get_current_user
import uuid

router = APIRouter(prefix="/auth", tags=["auth"])

# Sentinel UUID — pre-auth data is tagged with this
SENTINEL_UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check duplicates
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
    await db.flush()  # get user.id assigned

    # If this is the FIRST user, claim all legacy (sentinel) data
    if user_count == 0:
        await _claim_legacy_data(db, user.id)

    await db.commit()

    token = create_access_token(user.id, user.username)
    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        username=user.username,
        email=user.email,
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
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
    )


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return UserOut(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username,
        created_at=current_user.created_at,
    )


async def _claim_legacy_data(db: AsyncSession, user_id: uuid.UUID):
    """Transfer all pre-auth sentinel data to the first registered user."""
    sentinel = str(SENTINEL_UUID)
    uid = str(user_id)
    for table in [
        "problem_progress", "problem_attempts", "error_patterns",
        "ai_insights", "learning_milestones", "topic_mastery",
    ]:
        await db.execute(
            text(f"UPDATE {table} SET user_id = :uid WHERE user_id = :sentinel"),
            {"uid": uid, "sentinel": sentinel},
        )
