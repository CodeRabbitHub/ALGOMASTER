"""
Interview analytics API: self-assessments, spaced repetition, mistake log,
contest log, DS fluency, and composite interview readiness score.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime, timezone, timedelta
from typing import List
import uuid

from app.database import get_db
from app.models.user import User
from app.models.problem import Problem
from app.models.interview import (
    SelfAssessment, ReviewSchedule, MistakeLog, ContestLog, DSFluency,
    PATTERNS, BUG_CATEGORIES, MISTAKE_CATEGORIES, EDGE_CASES, DATA_STRUCTURES,
)
from app.schemas.interview import (
    SelfAssessmentIn, SelfAssessmentOut,
    ReviewCompleteIn, ReviewScheduleOut, ReviewsAddIn,
    MistakeIn, MistakeOut,
    ContestIn, ContestOut,
    DSFluencyIn, DSFluencyOut,
    ReadinessScoreOut,
)
from app.analytics.interview import (
    sm2_next, compute_readiness_score, get_pattern_stats, get_mistake_summary,
)
from app.core.deps import get_current_user

router = APIRouter(prefix="/interview", tags=["interview"])


# ── Meta: available options ───────────────────────────────────────────────────

@router.get("/options")
async def get_options():
    """Return all dropdown/checkbox options for the frontend."""
    return {
        "patterns": PATTERNS,
        "bug_categories": BUG_CATEGORIES,
        "mistake_categories": MISTAKE_CATEGORIES,
        "edge_cases": EDGE_CASES,
        "data_structures": DATA_STRUCTURES,
    }


# ── Self Assessment ───────────────────────────────────────────────────────────

@router.post("/assessment", response_model=SelfAssessmentOut)
async def create_assessment(
    body: SelfAssessmentIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sa = SelfAssessment(
        user_id=current_user.id,
        problem_id=body.problem_id,
        pattern_identified=body.pattern_identified,
        time_to_pattern_secs=body.time_to_pattern_secs,
        pattern_was_correct=body.pattern_was_correct,
        time_to_first_idea_secs=body.time_to_first_idea_secs,
        time_to_algorithm_secs=body.time_to_algorithm_secs,
        total_solve_time_secs=body.total_solve_time_secs,
        wrong_approaches=body.wrong_approaches or 0,
        hint_used=body.hint_used or False,
        did_panic=body.did_panic or False,
        complexity_initial_time=body.complexity_initial_time,
        complexity_final_time=body.complexity_final_time,
        complexity_final_space=body.complexity_final_space,
        compile_attempts=body.compile_attempts or 1,
        bugs_count=body.bugs_count or 0,
        bug_categories=body.bug_categories or [],
        debug_time_secs=body.debug_time_secs,
        communication_score=body.communication_score,
        edge_cases_checked=body.edge_cases_checked or [],
        edge_cases_before_coding=body.edge_cases_before_coding,
        new_learning=body.new_learning,
        confidence_after=body.confidence_after,
    )
    db.add(sa)

    # Optionally add to review schedule
    if body.add_to_review:
        existing = await db.execute(
            select(ReviewSchedule).where(
                ReviewSchedule.problem_id == body.problem_id,
                ReviewSchedule.user_id == current_user.id,
            )
        )
        if not existing.scalar_one_or_none():
            rs = ReviewSchedule(
                problem_id=body.problem_id,
                user_id=current_user.id,
                next_review_at=datetime.now(timezone.utc) + timedelta(days=1),
                interval_days=1.0,
                ease_factor=2.5,
                rep_count=0,
            )
            db.add(rs)

    await db.commit()
    await db.refresh(sa)
    return _sa_out(sa)


@router.get("/assessment/{problem_id}", response_model=SelfAssessmentOut)
async def get_assessment(
    problem_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SelfAssessment)
        .where(SelfAssessment.user_id == current_user.id)
        .where(SelfAssessment.problem_id == problem_id)
        .order_by(SelfAssessment.assessed_at.desc())
        .limit(1)
    )
    sa = result.scalar_one_or_none()
    if not sa:
        raise HTTPException(status_code=404, detail="No assessment found")
    return _sa_out(sa)


@router.get("/assessments", response_model=List[SelfAssessmentOut])
async def list_assessments(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SelfAssessment)
        .where(SelfAssessment.user_id == current_user.id)
        .order_by(SelfAssessment.assessed_at.desc())
        .limit(limit)
    )
    return [_sa_out(sa) for sa in result.scalars().all()]


def _sa_out(sa: SelfAssessment) -> dict:
    return {
        "id": str(sa.id),
        "problem_id": sa.problem_id,
        "assessed_at": sa.assessed_at,
        "pattern_identified": sa.pattern_identified,
        "time_to_pattern_secs": sa.time_to_pattern_secs,
        "pattern_was_correct": sa.pattern_was_correct,
        "complexity_initial_time": sa.complexity_initial_time,
        "complexity_final_time": sa.complexity_final_time,
        "complexity_final_space": sa.complexity_final_space,
        "compile_attempts": sa.compile_attempts,
        "bugs_count": sa.bugs_count,
        "bug_categories": sa.bug_categories or [],
        "communication_score": sa.communication_score,
        "edge_cases_checked": sa.edge_cases_checked or [],
        "edge_cases_before_coding": sa.edge_cases_before_coding,
        "new_learning": sa.new_learning,
        "confidence_after": sa.confidence_after,
        "hint_used": sa.hint_used,
        "wrong_approaches": sa.wrong_approaches,
        "did_panic": sa.did_panic,
    }


# ── Spaced Repetition ─────────────────────────────────────────────────────────

@router.get("/reviews/due", response_model=List[ReviewScheduleOut])
async def get_reviews_due(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return problems due for review (next_review_at <= now)."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(ReviewSchedule, Problem)
        .join(Problem, Problem.id == ReviewSchedule.problem_id)
        .where(ReviewSchedule.user_id == current_user.id)
        .where(ReviewSchedule.next_review_at <= now)
        .order_by(ReviewSchedule.next_review_at)
    )
    rows = result.all()
    return [_rs_out(rs, p) for rs, p in rows]


@router.get("/reviews/all", response_model=List[ReviewScheduleOut])
async def get_all_reviews(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ReviewSchedule, Problem)
        .join(Problem, Problem.id == ReviewSchedule.problem_id)
        .where(ReviewSchedule.user_id == current_user.id)
        .order_by(ReviewSchedule.next_review_at)
    )
    rows = result.all()
    return [_rs_out(rs, p) for rs, p in rows]


@router.post("/reviews/add")
async def add_to_review(
    body: ReviewsAddIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = await db.execute(
        select(ReviewSchedule).where(
            ReviewSchedule.problem_id == body.problem_id,
            ReviewSchedule.user_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none():
        return {"status": "already_scheduled"}

    rs = ReviewSchedule(
        problem_id=body.problem_id,
        user_id=current_user.id,
        next_review_at=datetime.now(timezone.utc) + timedelta(days=1),
        interval_days=1.0,
        ease_factor=2.5,
        rep_count=0,
    )
    db.add(rs)
    await db.commit()
    return {"status": "scheduled"}


@router.post("/reviews/complete")
async def complete_review(
    body: ReviewCompleteIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ReviewSchedule).where(
            ReviewSchedule.problem_id == body.problem_id,
            ReviewSchedule.user_id == current_user.id,
        )
    )
    rs = result.scalar_one_or_none()
    if not rs:
        raise HTTPException(status_code=404, detail="Not in review schedule")

    new_interval, new_ease, new_rep = sm2_next(
        rs.interval_days, rs.ease_factor, rs.rep_count, body.quality
    )
    rs.interval_days   = new_interval
    rs.ease_factor     = new_ease
    rs.rep_count       = new_rep
    rs.last_score      = body.quality
    rs.last_reviewed_at = datetime.now(timezone.utc)
    rs.next_review_at  = datetime.now(timezone.utc) + timedelta(days=new_interval)

    await db.commit()
    return {"next_review_at": rs.next_review_at, "interval_days": new_interval}


@router.delete("/reviews/{problem_id}")
async def remove_from_review(
    problem_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await db.execute(
        delete(ReviewSchedule).where(
            ReviewSchedule.problem_id == problem_id,
            ReviewSchedule.user_id == current_user.id,
        )
    )
    await db.commit()
    return {"status": "removed"}


def _rs_out(rs: ReviewSchedule, p: Problem) -> dict:
    return {
        "problem_id": rs.problem_id,
        "next_review_at": rs.next_review_at,
        "interval_days": rs.interval_days,
        "ease_factor": rs.ease_factor,
        "rep_count": rs.rep_count,
        "last_score": rs.last_score,
        "last_reviewed_at": rs.last_reviewed_at,
        "title": p.title,
        "difficulty": p.difficulty.value if hasattr(p.difficulty, "value") else p.difficulty,
        "category": p.category,
    }


# ── Mistake Log ───────────────────────────────────────────────────────────────

@router.post("/mistake", response_model=MistakeOut)
async def log_mistake(
    body: MistakeIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    m = MistakeLog(
        user_id=current_user.id,
        problem_id=body.problem_id,
        category=body.category,
        notes=body.notes,
    )
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return _mistake_out(m, None)


@router.get("/mistakes", response_model=List[MistakeOut])
async def list_mistakes(
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(MistakeLog, Problem)
        .outerjoin(Problem, Problem.id == MistakeLog.problem_id)
        .where(MistakeLog.user_id == current_user.id)
        .order_by(MistakeLog.occurred_at.desc())
        .limit(limit)
    )
    return [_mistake_out(m, p) for m, p in result.all()]


@router.get("/mistakes/summary")
async def mistake_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_mistake_summary(db, current_user.id)


def _mistake_out(m: MistakeLog, p) -> dict:
    return {
        "id": str(m.id),
        "problem_id": m.problem_id,
        "occurred_at": m.occurred_at,
        "category": m.category,
        "notes": m.notes,
        "problem_title": p.title if p else None,
    }


# ── Contest Log ───────────────────────────────────────────────────────────────

@router.post("/contest", response_model=ContestOut)
async def log_contest(
    body: ContestIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = ContestLog(
        user_id=current_user.id,
        platform=body.platform,
        contest_name=body.contest_name,
        contest_date=body.contest_date,
        rating=body.rating,
        rating_change=body.rating_change,
        global_rank=body.global_rank,
        questions_solved=body.questions_solved,
        total_questions=body.total_questions,
        penalty_mins=body.penalty_mins,
        notes=body.notes,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return _contest_out(c)


@router.get("/contests", response_model=List[ContestOut])
async def list_contests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ContestLog)
        .where(ContestLog.user_id == current_user.id)
        .order_by(ContestLog.contest_date.desc())
    )
    return [_contest_out(c) for c in result.scalars().all()]


@router.delete("/contest/{contest_id}")
async def delete_contest(
    contest_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await db.execute(
        delete(ContestLog).where(
            ContestLog.id == uuid.UUID(contest_id),
            ContestLog.user_id == current_user.id,
        )
    )
    await db.commit()
    return {"status": "deleted"}


def _contest_out(c: ContestLog) -> dict:
    return {
        "id": str(c.id),
        "platform": c.platform,
        "contest_name": c.contest_name,
        "contest_date": c.contest_date,
        "rating": c.rating,
        "rating_change": c.rating_change,
        "global_rank": c.global_rank,
        "questions_solved": c.questions_solved,
        "total_questions": c.total_questions,
        "penalty_mins": c.penalty_mins,
        "notes": c.notes,
        "created_at": c.created_at,
    }


# ── DS Fluency ────────────────────────────────────────────────────────────────

@router.get("/ds-fluency", response_model=List[DSFluencyOut])
async def get_fluency(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DSFluency)
        .where(DSFluency.user_id == current_user.id)
        .order_by(DSFluency.ds_name)
    )
    return [{"ds_name": f.ds_name, "rating": f.rating, "last_updated": f.last_updated}
            for f in result.scalars().all()]


@router.post("/ds-fluency")
async def update_fluency(
    body: DSFluencyIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upsert fluency ratings — accepts a dict of {ds_name: rating}."""
    for ds_name, rating in body.ratings.items():
        if not (1 <= rating <= 5):
            continue
        result = await db.execute(
            select(DSFluency).where(
                DSFluency.user_id == current_user.id,
                DSFluency.ds_name == ds_name,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.rating = rating
            existing.last_updated = datetime.now(timezone.utc)
        else:
            db.add(DSFluency(user_id=current_user.id, ds_name=ds_name, rating=rating))

    await db.commit()
    return {"status": "updated"}


# ── Readiness Score ───────────────────────────────────────────────────────────

@router.get("/readiness")
async def interview_readiness(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await compute_readiness_score(db, current_user.id)


# ── Pattern Stats ─────────────────────────────────────────────────────────────

@router.get("/pattern-stats")
async def pattern_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_pattern_stats(db, current_user.id)
