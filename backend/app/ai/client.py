from openai import AsyncOpenAI
from app.config import settings
from app.analytics.engine import get_overview_stats, get_error_patterns
from app.models.analytics import TopicMastery, AIInsight
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json, uuid, logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

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
        stats = await get_overview_stats(db, user_id)
        errors = await get_error_patterns(db, user_id)
        topics_q = await db.execute(
            select(TopicMastery)
            .where(TopicMastery.user_id == user_id)
            .order_by(TopicMastery.struggle_index.desc())
            .limit(10)
        )
        weak_topics = topics_q.scalars().all()
        context = f"""
User's AlgoMaster Learning Data:
- Total problems solved: {stats['total_solved']} / {stats['total_problems']}
- Easy: {stats['easy_solved']}, Medium: {stats['medium_solved']}, Hard: {stats['hard_solved']}
- First-attempt success rate: {stats['first_attempt_success_rate']}%
- Current streak: {stats['current_streak']} days
- Avg attempts per problem: {stats['avg_attempts_per_problem']}
- Solve velocity (last 7d): {stats['solve_velocity_7d']:.1f} problems/day
- Total time spent: {stats['total_time_secs'] // 3600}h {(stats['total_time_secs'] % 3600) // 60}m

Top error types: {json.dumps([e['error_category'] for e in errors[:5]])}

Weakest topics (by struggle index):
{chr(10).join(f"  - {t.category}: {t.solved}/{t.total_problems} solved, avg {t.avg_attempts:.1f} attempts, mastery {t.mastery_score:.0f}%" for t in weak_topics[:5])}
""".strip()
    else:
        stats = {}
        context = ""

    # Truncate description to keep prompt manageable
    desc_snippet = (problem_description or "")[:1500]
    failed_str = json.dumps(failed_cases or [], indent=2)

    prompts = {
        "weekly_report": (
            "You are a data-driven DSA coach. Based on the student's learning data, "
            "write a concise weekly performance report (under 400 words). Include: "
            "what they achieved this week, where they improved, where they struggled, "
            "and 3 specific actionable recommendations for next week. Be direct and specific.",
            context
        ),
        "study_plan": (
            "You are an expert DSA curriculum designer. Based on this student's performance data, "
            "create a personalized 2-week study plan. For each day, specify: which topic to study, "
            "which difficulty level to focus on, and why (based on their data). "
            "Prioritize high-impact areas. Format as a clear day-by-day schedule.",
            context
        ),
        "mistake_analysis": (
            "You are a DSA debugging expert. Analyze the student's error patterns and performance data. "
            "Identify the root causes of their most common mistakes. For each pattern, explain: "
            "what conceptual gap it reveals and how to fix it. Be specific and actionable.",
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
            "You are an expert DSA coach with access to the student's real learning data. "
            "Answer their question based on their actual performance. Be specific, not generic.",
            f"{context}\n\nStudent question: {message or ''}"
        ),
    }

    system_msg, user_msg = prompts.get(insight_type, prompts["chat"])

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg or "Please analyze my learning data."},
            ],
            max_tokens=1000,
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
        # Previously this returned the raw exception text as `content` with
        # a 200 status, so the frontend rendered it inside the same panel
        # used for genuine AI responses — a user had no way to tell a real
        # answer from a stack trace fragment. Signal failure explicitly
        # (ok: False) so the route can turn it into a proper error response
        # instead. Never leak str(e) to the client — it can contain request
        # internals; log it server-side and return a generic message.
        return {
            "ok": False,
            "content": None,
            "tokens_used": 0,
            "error": "The AI coach is temporarily unavailable. Please try again in a moment.",
        }
