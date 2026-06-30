from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List, Optional
from app.database import get_db
from app.models.problem import Problem, ProblemProgress
from app.models.user import User
from app.schemas.problem import ProblemOut, ProgressOut, ProgressUpdate
from app.core.deps import get_current_user
from sqlalchemy.sql import func

router = APIRouter(prefix="/problems", tags=["problems"])

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
    return result.scalars().all()

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
    return {p.problem_id: {
        "solved": p.solved_at is not None,
        "starred": p.is_starred,
        "attempts": p.total_attempts,
        "time_secs": p.total_time_secs,
        "confidence": p.confidence,
    } for p in progs}

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
    return p

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
