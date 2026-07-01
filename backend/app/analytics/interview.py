"""
Interview readiness analytics: SM-2 spaced repetition + composite readiness score.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
import uuid, math

from app.models.interview import (
    SelfAssessment, ReviewSchedule, MistakeLog, ContestLog, DSFluency,
    DATA_STRUCTURES,
)
from app.models.problem import Problem, ProblemProgress


# ── SM-2 Spaced Repetition ────────────────────────────────────────────────────

def sm2_next(
    interval: float,
    ease: float,
    rep_count: int,
    quality: int,          # 0–5: how well the user remembered
) -> tuple[float, float, int]:
    """
    Returns (new_interval_days, new_ease_factor, new_rep_count).
    Quality scale:
      0–2  = forgot / major difficulty  → reset
      3    = remembered with effort
      4    = correct with some hesitation
      5    = perfect recall
    """
    if quality < 3:
        return 1.0, max(1.3, ease - 0.2), 0

    new_ease = max(1.3, ease + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_rep  = rep_count + 1

    if new_rep == 1:
        new_interval = 1.0
    elif new_rep == 2:
        new_interval = 6.0
    else:
        new_interval = interval * new_ease

    return round(new_interval, 1), round(new_ease, 2), new_rep


# ── Composite Interview Readiness Score ───────────────────────────────────────

async def compute_readiness_score(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> Dict[str, Any]:
    """
    Computes a 0–100 composite interview readiness score from 7 dimensions.
    Returns the score, dimension breakdown, and a readiness label.
    """

    # ── 1. Speed (15 pts) ────────────────────────────────────────────────────
    # Compare avg solve time to targets: Easy 20min, Medium 35min, Hard 45min
    speed_score = await _speed_score(db, user_id)

    # ── 2. First-Attempt Accuracy (20 pts) ──────────────────────────────────
    accuracy_score = await _accuracy_score(db, user_id)

    # ── 3. Pattern Recognition Speed (15 pts) ────────────────────────────────
    pattern_score = await _pattern_score(db, user_id)

    # ── 4. Code Quality (15 pts) ─────────────────────────────────────────────
    quality_score = await _quality_score(db, user_id)

    # ── 5. Communication (15 pts) ────────────────────────────────────────────
    comm_score = await _communication_score(db, user_id)

    # ── 6. Edge Case Coverage (10 pts) ───────────────────────────────────────
    edge_score = await _edge_case_score(db, user_id)

    # ── 7. Topic Coverage Breadth (10 pts) ───────────────────────────────────
    breadth_score = await _breadth_score(db, user_id)

    total = (
        speed_score["points"]   +
        accuracy_score["points"] +
        pattern_score["points"] +
        quality_score["points"] +
        comm_score["points"]    +
        edge_score["points"]    +
        breadth_score["points"]
    )

    if total >= 85:
        label = "Interview Ready"
        label_color = "#3fb950"
    elif total >= 65:
        label = "Getting There"
        label_color = "#d29922"
    elif total >= 40:
        label = "Needs Practice"
        label_color = "#f85149"
    else:
        label = "Early Stage"
        label_color = "#8b949e"

    return {
        "total_score": round(total, 1),
        "label": label,
        "label_color": label_color,
        "dimensions": {
            "speed":        {**speed_score,    "max": 15, "label": "Solve Speed"},
            "accuracy":     {**accuracy_score, "max": 20, "label": "First-Attempt Accuracy"},
            "pattern":      {**pattern_score,  "max": 15, "label": "Pattern Recognition"},
            "code_quality": {**quality_score,  "max": 15, "label": "Code Quality"},
            "communication":{**comm_score,     "max": 15, "label": "Communication"},
            "edge_cases":   {**edge_score,     "max": 10, "label": "Edge Case Thinking"},
            "breadth":      {**breadth_score,  "max": 10, "label": "Topic Coverage"},
        },
    }


# ── Dimension helpers ─────────────────────────────────────────────────────────

async def _speed_score(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """Max 15 pts. Score based on avg solve time vs difficulty targets."""
    result = await db.execute(
        select(
            Problem.difficulty,
            func.avg(ProblemProgress.total_time_secs).label("avg_time"),
            func.count().label("cnt"),
        )
        .join(ProblemProgress, Problem.id == ProblemProgress.problem_id)
        .where(ProblemProgress.user_id == user_id)
        .where(ProblemProgress.solved_at.isnot(None))
        .where(ProblemProgress.total_time_secs > 0)
        .group_by(Problem.difficulty)
    )
    rows = {r.difficulty: (r.avg_time, r.cnt) for r in result.all()}

    targets = {"Easy": 20 * 60, "Medium": 35 * 60, "Hard": 45 * 60}
    weights = {"Easy": 0.2, "Medium": 0.5, "Hard": 0.3}
    total_weight, weighted_pct = 0.0, 0.0

    for diff, (avg, cnt) in rows.items():
        target = targets.get(diff, 30 * 60)
        pct = min(1.0, target / max(avg, 1))   # 1.0 if at or under target
        w = weights.get(diff, 0.33)
        weighted_pct += pct * w
        total_weight += w

    pct = (weighted_pct / total_weight) if total_weight > 0 else 0
    pts = round(pct * 15, 1)
    avg_total = sum(v[0] for v in rows.values()) / max(len(rows), 1)
    return {
        "points": pts,
        "pct": round(pct * 100),
        "detail": f"Avg solve time: {int(avg_total // 60)}m {int(avg_total % 60)}s" if rows else "No data yet",
        "raw": {d: f"{int(v[0]//60)}m" for d, v in rows.items()},
    }


async def _accuracy_score(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """Max 20 pts. First-attempt success rate."""
    total_q = await db.execute(
        select(func.count()).select_from(ProblemProgress)
        .where(ProblemProgress.user_id == user_id)
        .where(ProblemProgress.solved_at.isnot(None))
    )
    total = total_q.scalar() or 0

    first_q = await db.execute(
        select(func.count()).select_from(ProblemProgress)
        .where(ProblemProgress.user_id == user_id)
        .where(ProblemProgress.total_attempts == 1)
        .where(ProblemProgress.solved_at.isnot(None))
    )
    first_win = first_q.scalar() or 0

    rate = (first_win / total) if total > 0 else 0
    pts = round(rate * 20, 1)
    return {
        "points": pts,
        "pct": round(rate * 100),
        "detail": f"{first_win}/{total} problems solved on first attempt" if total else "No data yet",
        "raw": {"first_win": first_win, "total": total},
    }


async def _pattern_score(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """Max 15 pts. Based on self-assessments: correct pattern + speed."""
    result = await db.execute(
        select(
            func.count().label("total"),
            func.count().filter(SelfAssessment.pattern_was_correct == True).label("correct"),
            func.avg(SelfAssessment.time_to_pattern_secs).label("avg_time"),
        )
        .where(SelfAssessment.user_id == user_id)
        .where(SelfAssessment.pattern_identified.isnot(None))
    )
    row = result.one()

    if not row.total:
        return {"points": 0, "pct": 0, "detail": "No assessments yet", "raw": {}}

    accuracy = (row.correct or 0) / row.total
    # Target: identify pattern within 120 seconds
    avg_time = float(row.avg_time or 300)
    speed_pct = min(1.0, 120 / max(avg_time, 1))
    combined = accuracy * 0.6 + speed_pct * 0.4
    pts = round(combined * 15, 1)
    return {
        "points": pts,
        "pct": round(combined * 100),
        "detail": f"{row.correct}/{row.total} correct · avg {int(avg_time)}s to identify",
        "raw": {"correct": row.correct, "total": row.total, "avg_time_secs": int(avg_time or 0)},
    }


async def _quality_score(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """Max 15 pts. Based on compile_attempts (target: 1) and bug count."""
    result = await db.execute(
        select(
            func.avg(SelfAssessment.compile_attempts).label("avg_compile"),
            func.avg(SelfAssessment.bugs_count).label("avg_bugs"),
            func.count().label("total"),
        )
        .where(SelfAssessment.user_id == user_id)
    )
    row = result.one()

    if not row.total:
        return {"points": 0, "pct": 0, "detail": "No assessments yet", "raw": {}}

    avg_compile = float(row.avg_compile or 1)
    avg_bugs    = float(row.avg_bugs or 0)

    # Compile: 1 attempt = 100%, 5+ = 0%
    compile_pct = max(0, 1 - (avg_compile - 1) / 4)
    # Bugs: 0 = 100%, 5+ = 0%
    bugs_pct    = max(0, 1 - avg_bugs / 5)
    combined    = compile_pct * 0.5 + bugs_pct * 0.5
    pts         = round(combined * 15, 1)
    return {
        "points": pts,
        "pct": round(combined * 100),
        "detail": f"Avg {avg_compile:.1f} compile attempts · {avg_bugs:.1f} bugs/problem",
        "raw": {"avg_compile": round(avg_compile, 1), "avg_bugs": round(avg_bugs, 1)},
    }


async def _communication_score(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """Max 15 pts. Self-rated communication score (1–10)."""
    result = await db.execute(
        select(
            func.avg(SelfAssessment.communication_score).label("avg_score"),
            func.count().filter(SelfAssessment.communication_score.isnot(None)).label("total"),
        )
        .where(SelfAssessment.user_id == user_id)
    )
    row = result.one()

    if not row.total:
        return {"points": 0, "pct": 0, "detail": "No assessments yet", "raw": {}}

    avg = float(row.avg_score or 0)
    pts = round((avg / 10) * 15, 1)
    return {
        "points": pts,
        "pct": round((avg / 10) * 100),
        "detail": f"Avg communication score: {avg:.1f}/10",
        "raw": {"avg_score": round(avg, 1), "total": row.total},
    }


async def _edge_case_score(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """Max 10 pts. % of solves where edge cases were identified before coding."""
    result = await db.execute(
        select(
            func.count().label("total"),
            func.count().filter(SelfAssessment.edge_cases_before_coding == True).label("before"),
        )
        .where(SelfAssessment.user_id == user_id)
        .where(SelfAssessment.edge_cases_before_coding.isnot(None))
    )
    row = result.one()

    if not row.total:
        return {"points": 0, "pct": 0, "detail": "No assessments yet", "raw": {}}

    rate = (row.before or 0) / row.total
    pts  = round(rate * 10, 1)
    return {
        "points": pts,
        "pct": round(rate * 100),
        "detail": f"{row.before}/{row.total} problems: edge cases identified before coding",
        "raw": {"before": row.before, "total": row.total},
    }


async def _breadth_score(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """Max 10 pts. Topics with ≥1 solved / total topics."""
    cats_q = await db.execute(
        select(func.count(Problem.category.distinct()).label("total_cats"))
    )
    total_cats = cats_q.scalar() or 1

    solved_cats_q = await db.execute(
        select(func.count(Problem.category.distinct()).label("solved_cats"))
        .join(ProblemProgress, Problem.id == ProblemProgress.problem_id)
        .where(ProblemProgress.user_id == user_id)
        .where(ProblemProgress.solved_at.isnot(None))
    )
    solved_cats = solved_cats_q.scalar() or 0

    pct = solved_cats / total_cats
    pts = round(pct * 10, 1)
    return {
        "points": pts,
        "pct": round(pct * 100),
        "detail": f"{solved_cats}/{total_cats} topics attempted",
        "raw": {"solved_cats": solved_cats, "total_cats": total_cats},
    }


# ── Pattern analytics ─────────────────────────────────────────────────────────

async def get_pattern_stats(db: AsyncSession, user_id: uuid.UUID) -> List[Dict]:
    """Per-pattern: total uses, correct rate, avg recognition time."""
    result = await db.execute(
        select(
            SelfAssessment.pattern_identified,
            func.count().label("total"),
            func.count().filter(SelfAssessment.pattern_was_correct == True).label("correct"),
            func.avg(SelfAssessment.time_to_pattern_secs).label("avg_time"),
        )
        .where(SelfAssessment.user_id == user_id)
        .where(SelfAssessment.pattern_identified.isnot(None))
        .group_by(SelfAssessment.pattern_identified)
        .order_by(func.count().desc())
    )
    return [
        {
            "pattern": r.pattern_identified,
            "total": r.total,
            "correct": r.correct or 0,
            "accuracy_pct": round((r.correct or 0) / r.total * 100),
            "avg_time_secs": int(r.avg_time or 0),
        }
        for r in result.all()
    ]


# ── Mistake analytics ─────────────────────────────────────────────────────────

async def get_mistake_summary(db: AsyncSession, user_id: uuid.UUID) -> List[Dict]:
    result = await db.execute(
        select(
            MistakeLog.category,
            func.count().label("count"),
        )
        .where(MistakeLog.user_id == user_id)
        .group_by(MistakeLog.category)
        .order_by(func.count().desc())
    )
    return [{"category": r.category, "count": r.count} for r in result.all()]
