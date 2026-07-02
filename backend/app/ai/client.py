from openai import AsyncOpenAI
from app.config import settings
from app.analytics.engine import get_overview_stats, get_error_patterns
from app.models.analytics import TopicMastery, AIInsight
from app.models.problem import Problem, ProblemProgress
from app.models.attempt import ProblemAttempt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import json, uuid, logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

async def _build_rich_context(db: AsyncSession, user_id) -> str:
    """Gather comprehensive historical data for personalised AI analysis."""
    stats = await get_overview_stats(db, user_id)
    errors = await get_error_patterns(db, user_id)

    topics_q = await db.execute(
        select(TopicMastery)
        .where(TopicMastery.user_id == user_id)
        .order_by(TopicMastery.struggle_index.desc())
        .limit(15)
    )
    all_topics = topics_q.scalars().all()
    weak_topics = [t for t in all_topics if t.mastery_score < 60][:5]
    strong_topics = sorted(all_topics, key=lambda t: -t.mastery_score)[:3]

    # Recent solved problems (last 20, most recent first)
    recent_q = await db.execute(
        select(
            Problem.title,
            Problem.difficulty,
            Problem.category,
            ProblemProgress.total_attempts,
            ProblemProgress.total_time_secs,
            ProblemProgress.solved_at,
        )
        .join(Problem, ProblemProgress.problem_id == Problem.id)
        .where(ProblemProgress.user_id == user_id)
        .where(ProblemProgress.solved_at.isnot(None))
        .order_by(ProblemProgress.solved_at.desc())
        .limit(20)
    )
    recent = recent_q.all()

    # Re-attempt rate: problems that took > 1 attempt
    reattempt_q = await db.execute(
        select(func.count())
        .select_from(ProblemProgress)
        .where(ProblemProgress.user_id == user_id)
        .where(ProblemProgress.total_attempts > 1)
        .where(ProblemProgress.solved_at.isnot(None))
    )
    reattempt_count = reattempt_q.scalar() or 0

    # Average time per difficulty on solved problems
    diff_time_q = await db.execute(
        select(
            Problem.difficulty,
            func.avg(ProblemProgress.total_time_secs).label("avg_time"),
            func.avg(ProblemProgress.total_attempts).label("avg_att"),
        )
        .join(Problem, ProblemProgress.problem_id == Problem.id)
        .where(ProblemProgress.user_id == user_id)
        .where(ProblemProgress.solved_at.isnot(None))
        .group_by(Problem.difficulty)
    )
    diff_stats = {r.difficulty: {"avg_time": int(r.avg_time or 0), "avg_att": round(float(r.avg_att or 0), 1)}
                  for r in diff_time_q.all()}

    total_solved = stats['total_solved']
    reattempt_pct = round(reattempt_count / total_solved * 100, 1) if total_solved > 0 else 0

    recent_lines = "\n".join(
        f"  - {r.title} ({r.difficulty}, {r.category}): {r.total_attempts} attempt(s), "
        f"{r.total_time_secs // 60}m {r.total_time_secs % 60}s, "
        f"solved {r.solved_at.strftime('%Y-%m-%d') if r.solved_at else 'unknown'}"
        for r in recent[:10]
    )

    weak_lines = "\n".join(
        f"  - {t.category}: {t.solved}/{t.total_problems} solved, "
        f"avg {t.avg_attempts:.1f} attempts, mastery {t.mastery_score:.0f}%"
        for t in weak_topics
    ) or "  (none below 60% yet)"

    strong_lines = "\n".join(
        f"  - {t.category}: {t.mastery_score:.0f}% mastery"
        for t in strong_topics
    ) or "  (not enough data yet)"

    diff_lines = "\n".join(
        f"  - {diff}: avg {v['avg_time'] // 60}m {v['avg_time'] % 60}s, avg {v['avg_att']} attempts"
        for diff, v in diff_stats.items()
    ) or "  (no data)"

    return f"""=== Student's AlgoMaster Performance Data ===

OVERALL PROGRESS
- Problems solved: {stats['total_solved']} / {stats['total_problems']}
- Easy: {stats['easy_solved']}/{stats.get('easy_total', '?')}, Medium: {stats['medium_solved']}/{stats.get('medium_total', '?')}, Hard: {stats['hard_solved']}/{stats.get('hard_total', '?')}
- Total time invested: {stats['total_time_secs'] // 3600}h {(stats['total_time_secs'] % 3600) // 60}m
- Current streak: {stats['current_streak']} days (longest: {stats['longest_streak']} days)

EFFICIENCY METRICS
- First-attempt success rate: {stats['first_attempt_success_rate']}%
- Avg attempts per problem: {stats['avg_attempts_per_problem']}
- Problems requiring re-attempts: {reattempt_count} ({reattempt_pct}% of solved)
- Solve velocity (7d): {stats['solve_velocity_7d']:.1f}/day, (30d): {stats['solve_velocity_30d']:.1f}/day

AVERAGE TIME & ATTEMPTS BY DIFFICULTY
{diff_lines}

TOP ERROR TYPES (most frequent mistakes)
{json.dumps([{"type": e['error_category'], "count": e['count']} for e in errors[:7]], indent=2)}

STRONGEST TOPICS
{strong_lines}

WEAKEST TOPICS (needs focus)
{weak_lines}

RECENT SOLVES (last 10, newest first)
{recent_lines or '  (none yet)'}
""".strip()


async def get_ai_response(
    insight_type: str,
    db: AsyncSession,
    user_id=None,
    message: str = None,
    code: str = None,
    problem_title: str = None,
    problem_description: str = None,
    failed_cases: list = None,
) -> dict:
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("sk-your"):
        return {
            "ok": True,
            "configured": False,
            "content": "⚠️ OpenAI API key not configured. Go to **Settings** to add your key — no restart needed.",
            "tokens_used": 0,
        }

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    # Build context from real data (skip for problem-specific insight types)
    problem_only = insight_type in ("hint", "mistake_explain", "code_review")
    if not problem_only:
        context = await _build_rich_context(db, user_id)
    else:
        context = ""

    # Truncate description to keep prompt manageable
    desc_snippet = (problem_description or "")[:1500]
    failed_str = json.dumps(failed_cases or [], indent=2)

    prompts = {
        "weekly_report": (
            "You are a data-driven DSA coach with full access to the student's real performance history.\n\n"
            "Write a personalised weekly performance report (under 450 words). Structure it as:\n"
            "1. THIS WEEK — what they achieved (reference specific numbers)\n"
            "2. STRENGTHS — what they're genuinely good at (cite topics/metrics)\n"
            "3. WEAK SPOTS — where they're struggling and why (cite error patterns, low-mastery topics)\n"
            "4. NEXT WEEK — exactly 3 actionable recommendations (specific topics, difficulty levels, and why)\n\n"
            "Be direct, specific, and data-driven. Avoid generic advice.",
            context
        ),
        "study_plan": (
            "You are an expert DSA curriculum designer with the student's full performance data.\n\n"
            "Create a personalised 2-week study plan. Rules:\n"
            "- Prioritise their weakest topics (cite the data)\n"
            "- Match difficulty to their current success rate (don't recommend Hard if first-attempt rate < 50%)\n"
            "- For each day: topic, difficulty, problem count, and 1-sentence rationale from their data\n"
            "- Include 1 rest day per week\n"
            "- Keep it achievable based on their solve velocity\n\n"
            "Format: Day 1 | Topic | Difficulty | Goal | Why",
            context
        ),
        "mistake_analysis": (
            "You are a DSA coach analysing this student's error patterns and performance data.\n\n"
            "Provide a deep root-cause analysis:\n"
            "1. PATTERN SUMMARY — rank their top 3 error types by frequency (cite counts)\n"
            "2. ROOT CAUSES — for each error type: what conceptual gap does it reveal?\n"
            "3. TOPIC GAPS — which weak topics correlate with which errors?\n"
            "4. FIX PLAN — for each gap: one concrete drill or exercise to address it\n\n"
            "Ground every claim in the data. Under 500 words.",
            context
        ),
        "hint": (
            "You are an expert DSA tutor. Give helpful hints for this problem WITHOUT revealing the solution or writing any code.\n\n"
            f"Problem: {problem_title}\n\n{desc_snippet}\n\n"
            "Provide 3 progressive hints:\n"
            "- Hint 1: A gentle nudge about which algorithm family or data structure to consider\n"
            "- Hint 2: More specific guidance about the approach or key insight\n"
            "- Hint 3: A near-complete conceptual walkthrough (still no code)\n\n"
            "Format exactly as:\nHint 1: ...\nHint 2: ...\nHint 3: ...",
            ""
        ),
        "mistake_explain": (
            "You are an expert DSA debugging coach. The student's code failed some test cases.\n\n"
            f"Problem: {problem_title}\n\n"
            f"Student's code:\n```python\n{code or ''}\n```\n\n"
            f"Failed test cases:\n{failed_str}\n\n"
            "Explain clearly:\n"
            "1. Why the code is failing (the specific bug or logical error)\n"
            "2. What conceptual misunderstanding caused it\n"
            "3. A concrete direction to fix it — no solution code, just the key insight needed\n\n"
            "Be direct and specific. Under 300 words.",
            ""
        ),
        "code_review": (
            f"You are a senior software engineer doing a code review. Review this Python solution for '{problem_title}':\n\n"
            f"```python\n{code or ''}\n```\n\n"
            "Provide: 1) Time/space complexity analysis, 2) What the student did correctly, "
            "3) What could be improved, 4) An alternative approach if one exists. Be constructive.",
            ""
        ),
        "chat": (
            "You are an expert DSA coach with full access to the student's real learning data. "
            "Answer their specific question using their actual stats. Be direct and specific — "
            "reference their numbers, topics, or error patterns when relevant. Avoid generic advice.",
            f"{context}\n\nStudent question: {message or ''}"
        ),
    }

    system_msg, user_msg = prompts.get(insight_type, prompts["chat"])

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg or "Please analyse my learning data."},
            ],
            max_tokens=1200,
            temperature=0.7,
        )
        content = response.choices[0].message.content
        tokens = response.usage.total_tokens

        # Save to DB
        insight = AIInsight(
            insight_type=insight_type,
            user_id=user_id,
            content=content,
            input_context={"problem_title": problem_title},
            tokens_used=tokens,
            model=settings.OPENAI_MODEL,
        )
        db.add(insight)
        await db.commit()

        return {"ok": True, "content": content, "tokens_used": tokens, "id": str(insight.id)}
    except Exception as e:
        logger.exception(
            "OpenAI call failed: insight_type=%s user_id=%s", insight_type, user_id
        )
        return {
            "ok": False,
            "content": None,
            "tokens_used": 0,
            "error": "The AI coach is temporarily unavailable. Please try again in a moment.",
        }
