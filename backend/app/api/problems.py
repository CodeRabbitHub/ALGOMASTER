from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List, Optional
from app.database import get_db
from app.models.problem import Problem, ProblemProgress
from app.models.user import User
from app.schemas.problem import ProblemOut, ProgressOut, ProgressUpdate, PUBLIC_TEST_CASE_LIMIT
from app.core.deps import get_current_user
from sqlalchemy.sql import func

router = APIRouter(prefix="/problems", tags=["problems"])


def _public_problem_out(p: Problem) -> ProblemOut:
    """
    Build the client-facing representation of a problem, truncating
    test_cases to the public/example subset. This builds a fresh
    ProblemOut from individual fields rather than letting FastAPI
    auto-serialize the ORM object (response_model=ProblemOut with
    from_attributes) — the latter would ship the full, "hidden" test
    suite (including every expected output) to the browser. Building a
    plain schema object (not the ORM instance) also means slicing
    test_cases here never risks SQLAlchemy treating it as a change to
    persist back to the database.
    """
    return ProblemOut(
        id=p.id,
        slug=p.slug,
        title=p.title,
        difficulty=p.difficulty.value if hasattr(p.difficulty, "value") else p.difficulty,
        category=p.category,
        subcategory=p.subcategory,
        leetcode_url=p.leetcode_url,
        description=p.description or "",
        constraints=p.constraints or "",
        starter_code=p.starter_code or "",
        test_cases=(p.test_cases or [])[:PUBLIC_TEST_CASE_LIMIT],
        hints=p.hints or [],
        tags=p.tags or [],
        is_new=p.is_new,
    )


@router.get("", response_model=List[ProblemOut])
async def list_problems(
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Problem)
    if category:
        q = q.where(Problem.category == category)
    if difficulty:
        q = q.where(Problem.difficulty == difficulty)
    q = q.order_by(Problem.category, Problem.id)
    result = await db.execute(q)
    return [_public_problem_out(p) for p in result.scalars().all()]

@router.get("/categories")
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Problem.category, func.count(Problem.id).label("count")).group_by(Problem.category).order_by(Problem.category)
    result = await db.execute(q)
    return [{"category": r.category, "count": r.count} for r in result.all()]

@router.get("/progress/all")
async def get_all_progress(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ProblemProgress).where(ProblemProgress.user_id == current_user.id)
    )
    progs = result.scalars().all()
    return [
        {
            "problem_id": p.problem_id,
            "solved_at": p.solved_at.isoformat() if p.solved_at else None,
            "is_starred": p.is_starred,
            "total_attempts": p.total_attempts,
            "total_time_secs": p.total_time_secs,
            "confidence": p.confidence,
        }
        for p in progs
    ]

@router.get("/{problem_id}", response_model=ProblemOut)
async def get_problem(
    problem_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Problem).where(Problem.id == problem_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Problem not found")
    return _public_problem_out(p)

@router.get("/{problem_id}/progress", response_model=Optional[ProgressOut])
async def get_progress(
    problem_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ProblemProgress).where(
            ProblemProgress.problem_id == problem_id,
            ProblemProgress.user_id == current_user.id,
        )
    )
    return result.scalar_one_or_none()

@router.patch("/{problem_id}/progress", response_model=ProgressOut)
async def update_progress(
    problem_id: int,
    update_data: ProgressUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ProblemProgress).where(
            ProblemProgress.problem_id == problem_id,
            ProblemProgress.user_id == current_user.id,
        )
    )
    prog = result.scalar_one_or_none()

    if not prog:
        prog = ProblemProgress(problem_id=problem_id, user_id=current_user.id)
        db.add(prog)
        await db.flush()

    update_dict = update_data.model_dump(exclude_none=True)
    for k, v in update_dict.items():
        setattr(prog, k, v)

    await db.commit()
    await db.refresh(prog)
    return prog

@router.post("/{problem_id}/star")
async def toggle_star(
    problem_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ProblemProgress).where(
            ProblemProgress.problem_id == problem_id,
            ProblemProgress.user_id == current_user.id,
        )
    )
    prog = result.scalar_one_or_none()
    if not prog:
        prog = ProblemProgress(problem_id=problem_id, user_id=current_user.id, is_starred=True)
        db.add(prog)
    else:
        prog.is_starred = not prog.is_starred
    await db.commit()
    return {"is_starred": prog.is_starred}
