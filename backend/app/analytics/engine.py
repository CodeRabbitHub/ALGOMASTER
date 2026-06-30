from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text, case
from sqlalchemy.sql.expression import literal
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from app.models.problem import Problem, ProblemProgress
from app.models.attempt import ProblemAttempt, ErrorPattern
from app.models.analytics import TopicMastery, LearningMilestone
import math, uuid

async def get_overview_stats(db: AsyncSession, user_id: uuid.UUID) -> Dict[str, Any]:
    # Total problems
    total_q = await db.execute(select(func.count()).select_from(Problem))
    total_problems = total_q.scalar() or 0

    # Solved by difficulty (scoped to user)
    solved_q = await db.execute(
        select(Problem.difficulty, func.count().label("cnt"))
        .join(ProblemProgress, Problem.id == ProblemProgress.problem_id)
        .where(ProblemProgress.user_id == user_id)
        .where(ProblemProgress.solved_at.isnot(None))
        .group_by(Problem.difficulty)
    )
    solved_by_diff = {r.difficulty: r.cnt for r in solved_q.all()}

    # Total attempts and time (scoped to user)
    agg_q = await db.execute(
        select(
            func.count().label("total_attempts"),
            func.coalesce(func.sum(ProblemProgress.total_time_secs), 0).label("total_time"),
            func.coalesce(func.sum(
                case((ProblemProgress.total_attempts == 1, 1), else_=0)
            ), 0).label("first_win"),
        ).select_from(ProblemProgress)
        .where(ProblemProgress.user_id == user_id)
    )
    agg = agg_q.one()

    total_solved = sum(solved_by_diff.values())
    first_attempt_rate = (agg.first_win / total_solved * 100) if total_solved > 0 else 0.0

    # Velocity
    now = datetime.now(timezone.utc)
    v7_q = await db.execute(
        select(func.count()).select_from(ProblemProgress)
        .where(ProblemProgress.user_id == user_id)
        .where(ProblemProgress.solved_at >= now - timedelta(days=7))
    )
    v30_q = await db.execute(
        select(func.count()).select_from(ProblemProgress)
        .where(ProblemProgress.user_id == user_id)
        .where(ProblemProgress.solved_at >= now - timedelta(days=30))
    )
    v7 = (v7_q.scalar() or 0) / 7.0
    v30 = (v30_q.scalar() or 0) / 30.0

    streak, longest = await _compute_streak(db, user_id)
    avg_attempts = (agg.total_attempts / total_solved) if total_solved > 0 else 0.0

    return {
        "total_problems": total_problems,
        "total_solved": total_solved,
        "easy_solved": solved_by_diff.get("Easy", 0),
        "medium_solved": solved_by_diff.get("Medium", 0),
        "hard_solved": solved_by_diff.get("Hard", 0),
        "total_attempts": agg.total_attempts,
        "total_time_secs": agg.total_time,
        "first_attempt_success_rate": round(first_attempt_rate, 1),
        "current_streak": streak,
        "longest_streak": longest,
        "avg_attempts_per_problem": round(avg_attempts, 2),
        "solve_velocity_7d": round(v7, 2),
        "solve_velocity_30d": round(v30, 2),
    }

async def get_daily_stats(db: AsyncSession, days: int = 90, user_id: uuid.UUID = None) -> List[Dict]:
    """
    Returns per-user daily stats.
    NOTE: The TimescaleDB continuous aggregate (daily_stats) has no user_id dimension,
    so we always use the raw per-user query for correctness in multi-user mode.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    filters = [ProblemAttempt.submitted_at >= since]
    if user_id:
        filters.append(ProblemAttempt.user_id == user_id)
    result = await db.execute(
        select(
            func.date_trunc('day', ProblemAttempt.submitted_at).label("day"),
            func.count().label("total_attempts"),
            func.count().filter(ProblemAttempt.is_correct == True).label("solved"),
            func.count().filter(
                (ProblemAttempt.is_first_attempt == True) & (ProblemAttempt.is_correct == True)
            ).label("first_attempt_wins"),
            func.count(ProblemAttempt.problem_id.distinct()).label("problems_touched"),
            func.coalesce(func.sum(ProblemAttempt.time_spent_secs), 0).label("total_time_secs"),
            func.count().filter(ProblemAttempt.is_correct == False).label("errors_count"),
        )
        .where(*filters)
        .group_by(text("day"))
        .order_by(text("day"))
    )
    return [dict(r._mapping) for r in result.all()]

async def get_error_patterns(db: AsyncSession, user_id: uuid.UUID = None) -> List[Dict]:
    q = select(
        ErrorPattern.error_category,
        func.count().label("count"),
    ).group_by(ErrorPattern.error_category).order_by(func.count().desc()).limit(20)
    if user_id:
        q = q.where(ErrorPattern.user_id == user_id)
    result = await db.execute(q)
    return [{"error_category": r.error_category, "count": r.count} for r in result.all()]

async def refresh_topic_mastery(db: AsyncSession, user_id: uuid.UUID):
    """Recompute topic_mastery table for a specific user (skips if data is < 5 min old)."""
    last_q = await db.execute(
        select(func.max(TopicMastery.last_updated)).where(TopicMastery.user_id == user_id)
    )
    last = last_q.scalar()
    if last and (datetime.now(timezone.utc) - last) < timedelta(minutes=5):
        return  # data is fresh enough — skip the ~177 round-trips

    categories_q = await db.execute(
        select(Problem.category, func.count().label("total"))
        .group_by(Problem.category)
    )
    categories = {r.category: r.total for r in categories_q.all()}

    for cat, total in categories.items():
        solved_q = await db.execute(
            select(Problem.difficulty, func.count().label("cnt"))
            .join(ProblemProgress, Problem.id == ProblemProgress.problem_id)
            .where(Problem.category == cat)
            .where(ProblemProgress.user_id == user_id)
            .where(ProblemProgress.solved_at.isnot(None))
            .group_by(Problem.difficulty)
        )
        s = {r.difficulty: r.cnt for r in solved_q.all()}
        solved = sum(s.values())

        stats_q = await db.execute(
            select(
                func.avg(ProblemProgress.total_attempts).label("avg_att"),
                func.avg(ProblemProgress.total_time_secs).label("avg_time"),
            )
            .join(Problem, Problem.id == ProblemProgress.problem_id)
            .where(Problem.category == cat)
            .where(ProblemProgress.user_id == user_id)
            .where(ProblemProgress.total_attempts > 0)
        )
        stats = stats_q.one()
        avg_att = float(stats.avg_att or 0)
        avg_time = int(stats.avg_time or 0)

        struggle = (avg_att * (avg_time / 60)) / max(solved, 1)
        completion_pct = (solved / total) * 100 if total > 0 else 0
        difficulty_bonus = (s.get("Hard", 0) * 3 + s.get("Medium", 0) * 2 + s.get("Easy", 0)) / max(total, 1) * 20
        penalty = min(struggle * 5, 30)
        mastery = max(0, min(100, completion_pct * 0.7 + difficulty_bonus - penalty))

        existing = await db.execute(
            select(TopicMastery).where(
                TopicMastery.category == cat,
                TopicMastery.user_id == user_id,
            )
        )
        tm = existing.scalar_one_or_none()
        if tm:
            tm.total_problems = total; tm.solved = solved
            tm.easy_solved = s.get("Easy", 0); tm.medium_solved = s.get("Medium", 0)
            tm.hard_solved = s.get("Hard", 0); tm.avg_attempts = round(avg_att, 2)
            tm.avg_time_secs = avg_time; tm.struggle_index = round(struggle, 3)
            tm.mastery_score = round(mastery, 1); tm.last_updated = datetime.now(timezone.utc)
        else:
            db.add(TopicMastery(
                category=cat, user_id=user_id, total_problems=total, solved=solved,
                easy_solved=s.get("Easy", 0), medium_solved=s.get("Medium", 0),
                hard_solved=s.get("Hard", 0), avg_attempts=round(avg_att, 2),
                avg_time_secs=avg_time, struggle_index=round(struggle, 3),
                mastery_score=round(mastery, 1),
            ))
    await db.commit()

async def check_and_award_milestones(db: AsyncSession, user_id: uuid.UUID) -> List[Dict]:
    stats = await get_overview_stats(db, user_id)
    new_milestones = []
    solved = stats["total_solved"]

    milestones_map = {
        1: ("first_solve", "🎉 First problem solved! The journey begins."),
        10: ("solved_10", "🔥 10 problems solved — you're on your way!"),
        25: ("solved_25", "💪 25 problems — quarter century!"),
        50: ("solved_50", "⚡ 50 problems solved — halfway to 100!"),
        100: ("solved_100", "🏆 100 problems! You're in the top tier."),
        250: ("solved_250", "🚀 250 problems — elite level!"),
        600: ("solved_600", "👑 All 600 problems solved! Legendary."),
    }

    for threshold, (mtype, desc) in milestones_map.items():
        if solved >= threshold:
            existing = await db.execute(
                select(LearningMilestone).where(
                    LearningMilestone.milestone_type == mtype,
                    LearningMilestone.user_id == user_id,
                )
            )
            if not existing.scalar_one_or_none():
                m = LearningMilestone(
                    milestone_type=mtype, description=desc,
                    extra_data={"solved": solved}, user_id=user_id,
                )
                db.add(m)
                new_milestones.append({"type": mtype, "description": desc})

    if new_milestones:
        await db.commit()
    return new_milestones

async def _compute_streak(db: AsyncSession, user_id: uuid.UUID):
    result = await db.execute(
        select(func.date_trunc('day', ProblemProgress.solved_at).label("day"))
        .where(ProblemProgress.user_id == user_id)
        .where(ProblemProgress.solved_at.isnot(None))
        .distinct()
        .order_by(text("day DESC"))
    )
    days = [r.day.date() for r in result.all()]
    if not days:
        return 0, 0

    today = datetime.now(timezone.utc).date()
    streak = 0; longest = 0; cur = 0; prev = None

    for day in sorted(days, reverse=True):
        if prev is None:
            if day >= today - timedelta(days=1):
                streak = 1; cur = 1
        else:
            diff = (prev - day).days
            if diff == 1:
                cur += 1
                if prev >= today - timedelta(days=1):
                    streak = cur
            else:
                cur = 1
        longest = max(longest, cur)
        prev = day

    return streak, longest
