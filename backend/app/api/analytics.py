from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid
from app.database import get_db, AsyncSessionLocal
from app.models.analytics import TopicMastery, LearningMilestone
from app.models.user import User
from app.schemas.analytics import TopicMasteryOut, OverviewStatsOut, DailyStatOut, MilestoneOut, ErrorPatternOut
from app.analytics.engine import (
    get_overview_stats, get_daily_stats, get_error_patterns,
    refresh_topic_mastery, check_and_award_milestones
)
from app.core.deps import get_current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])

async def _refresh_topic_mastery_bg(user_id: uuid.UUID):
    """Background wrapper that opens its own DB session (request session is already closed)."""
    async with AsyncSessionLocal() as db:
        await refresh_topic_mastery(db, user_id)

@router.get("/overview")
async def overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_overview_stats(db, current_user.id)

@router.get("/daily")
async def daily_stats(
    days: int = 90,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_daily_stats(db, days, current_user.id)

@router.get("/topic-mastery", response_model=List[TopicMasteryOut])
async def topic_mastery(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(TopicMastery)
        .where(TopicMastery.user_id == current_user.id)
        .order_by(TopicMastery.mastery_score.desc())
    )
    topics = result.scalars().all()
    background_tasks.add_task(_refresh_topic_mastery_bg, current_user.id)
    return topics

@router.post("/topic-mastery/refresh")
async def refresh_mastery(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await refresh_topic_mastery(db, current_user.id)
    return {"status": "refreshed"}

@router.get("/error-patterns", response_model=List[ErrorPatternOut])
async def error_patterns(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patterns = await get_error_patterns(db, current_user.id)
    return [ErrorPatternOut(
        error_category=p["error_category"] or "Other",
        count=p["count"],
    ) for p in patterns]

@router.get("/milestones", response_model=List[MilestoneOut])
async def milestones(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(LearningMilestone)
        .where(LearningMilestone.user_id == current_user.id)
        .order_by(LearningMilestone.achieved_at.desc())
    )
    ms = result.scalars().all()
    return [MilestoneOut(
        id=str(m.id), achieved_at=m.achieved_at,
        milestone_type=m.milestone_type, description=m.description,
        metadata=m.extra_data or {}
    ) for m in ms]

@router.post("/milestones/check")
async def check_milestones(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new = await check_and_award_milestones(db, current_user.id)
    return {"new_milestones": new}
