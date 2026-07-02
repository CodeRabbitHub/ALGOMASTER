from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.schemas.analytics import AIInsightRequest, AIInsightOut
from app.models.analytics import AIInsight
from app.models.problem import Problem
from app.models.user import User
from app.ai.client import get_ai_response
from app.core.deps import get_current_user
from app.core.limiter import limiter, key_func_user_or_ip
from typing import List

router = APIRouter(prefix="/ai", tags=["ai"])

# Every call here triggers a real, billed OpenAI request against the
# instance's single shared API key (see settings.py) — cap it per user so
# one account can't run up an unbounded bill or starve everyone else's
# access. 20/hour is generous for interactive use (hints, reviews, chat)
# while still bounding worst-case cost.
@router.post("/insight")
@limiter.limit("20/hour", key_func=key_func_user_or_ip)
async def generate_insight(
    request: Request,
    req: AIInsightRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    problem_title = None
    problem_description = None
    if req.problem_id:
        p = await db.execute(select(Problem).where(Problem.id == req.problem_id))
        prob = p.scalar_one_or_none()
        if prob:
            problem_title = prob.title
            problem_description = (prob.description or "")[:2000]

    result = await get_ai_response(
        insight_type=req.insight_type,
        db=db,
        user_id=current_user.id,
        message=req.message,
        code=req.code,
        problem_title=problem_title,
        problem_description=problem_description,
        failed_cases=req.failed_cases,
    )
    if not result.get("ok", True):
        # A genuine OpenAI failure (bad key, rate limit, network error) —
        # surface it as a real error response rather than a 200 whose
        # "content" happens to be an error string. The frontend renders
        # this distinctly from a normal AI response (see ProblemPage.jsx /
        # AIInsightsPanel.jsx).
        raise HTTPException(status_code=502, detail=result.get("error") or "AI service unavailable.")
    return result

@router.get("/history", response_model=List[AIInsightOut])
async def insight_history(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(AIInsight)
        .where(AIInsight.user_id == current_user.id)
        .order_by(AIInsight.generated_at.desc())
        .limit(limit)
    )
    insights = result.scalars().all()
    return [AIInsightOut(
        id=str(i.id), generated_at=i.generated_at, insight_type=i.insight_type,
        content=i.content, tokens_used=i.tokens_used, model=i.model
    ) for i in insights]
