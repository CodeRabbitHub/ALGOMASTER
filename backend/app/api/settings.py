from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from cryptography.fernet import InvalidToken

from app.database import get_db
from app.config import settings
from app.models.settings import AppSetting
from app.models.user import User
from app.core.deps import get_current_user
from app.core.encryption import encrypt, decrypt

router = APIRouter(prefix="/settings", tags=["settings"])

OPENAI_KEY_NAME = "openai_api_key"


# ── Schemas ───────────────────────────────────────────────────────────────────

class OpenAIKeyRequest(BaseModel):
    api_key: str

class OpenAIKeyStatus(BaseModel):
    configured: bool          # whether a key is stored in the DB
    source: str               # "database" | "environment" | "none"


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_stored_row(db: AsyncSession) -> AppSetting | None:
    result = await db.execute(
        select(AppSetting).where(AppSetting.key == OPENAI_KEY_NAME)
    )
    return result.scalar_one_or_none()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/openai-key", response_model=OpenAIKeyStatus)
async def get_openai_key_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return whether an OpenAI key is configured and where it came from."""
    row = await _get_stored_row(db)
    if row:
        return {"configured": True, "source": "database"}
    if settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-your"):
        return {"configured": True, "source": "environment"}
    return {"configured": False, "source": "none"}


@router.post("/openai-key", response_model=OpenAIKeyStatus)
async def set_openai_key(
    body: OpenAIKeyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Encrypt and persist the OpenAI API key. Also activates it immediately in memory."""
    key = body.api_key.strip()
    if not key.startswith("sk-"):
        raise HTTPException(400, "Invalid API key — must start with 'sk-'")

    encrypted = encrypt(key, settings.SECRET_KEY)

    row = await _get_stored_row(db)
    if row:
        row.value = encrypted
    else:
        db.add(AppSetting(key=OPENAI_KEY_NAME, value=encrypted))
    await db.commit()

    # Activate immediately — no restart needed
    settings.OPENAI_API_KEY = key

    return {"configured": True, "source": "database"}


@router.delete("/openai-key")
async def delete_openai_key(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove the stored key from the database."""
    row = await _get_stored_row(db)
    if not row:
        raise HTTPException(404, "No key stored in database")
    await db.delete(row)
    await db.commit()

    # Clear from memory if it came from the DB (don't clobber env-var key)
    settings.OPENAI_API_KEY = ""

    return {"status": "deleted"}


# ── Loader called at startup ──────────────────────────────────────────────────

async def load_openai_key_from_db(db: AsyncSession) -> bool:
    """
    Called once at startup. If OPENAI_API_KEY is not set via env var,
    tries to load and decrypt it from the database.
    Returns True if a key was loaded.
    """
    if settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-your"):
        return True  # already configured via environment

    result = await db.execute(
        select(AppSetting).where(AppSetting.key == OPENAI_KEY_NAME)
    )
    row = result.scalar_one_or_none()
    if not row:
        return False

    try:
        decrypted = decrypt(row.value, settings.SECRET_KEY)
        settings.OPENAI_API_KEY = decrypted
        return True
    except (InvalidToken, Exception):
        # Key was encrypted with a different SECRET_KEY — can't decrypt
        return False
