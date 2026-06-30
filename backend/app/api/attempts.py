from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from typing import List
import httpx, uuid
from datetime import datetime, timezone
from app.database import get_db
from app.models.attempt import ProblemAttempt, ErrorPattern
from app.models.problem import Problem, ProblemProgress
from app.models.user import User
from app.schemas.problem import RunCodeRequest, RunCodeResponse
from app.schemas.analytics import AttemptOut
from app.core.deps import get_current_user
from app.config import settings

router = APIRouter(prefix="/attempts", tags=["attempts"])

@router.post("/run", response_model=RunCodeResponse)
async def run_code(
    req: RunCodeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send code to isolated code-runner and log the attempt."""
    p_result = await db.execute(select(Problem).where(Problem.id == req.problem_id))
    problem = p_result.scalar_one_or_none()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    all_cases = problem.test_cases or []
    cases_to_run = all_cases if req.mode == "submit" else all_cases[:3]

    payload = {"code": req.code, "test_cases": cases_to_run}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(f"{settings.CODE_RUNNER_URL}/execute", json=payload)
            runner_data = resp.json()
    except Exception as e:
        runner_data = {"stdout": "", "stderr": str(e), "is_correct": False, "test_results": [], "exec_time_ms": 0}

    count_q = await db.execute(
        select(func.count()).where(
            ProblemAttempt.problem_id == req.problem_id,
            ProblemAttempt.user_id == current_user.id,
        )
    )
    prev_count = count_q.scalar() or 0
    is_first = prev_count == 0

    attempt_id = uuid.uuid4()
    attempt = ProblemAttempt(
        id=attempt_id,
        user_id=current_user.id,
        problem_id=req.problem_id,
        submitted_at=datetime.now(timezone.utc),
        attempt_number=prev_count + 1,
        time_spent_secs=req.time_spent_secs,
        code=req.code,
        is_correct=runner_data.get("is_correct", False),
        is_first_attempt=is_first,
        error_type=_classify_error(runner_data.get("stderr", "")),
        error_message=runner_data.get("stderr", ""),
        stdout=runner_data.get("stdout", ""),
        test_results=runner_data.get("test_results", []),
    )
    db.add(attempt)

    prog_q = await db.execute(
        select(ProblemProgress).where(
            ProblemProgress.problem_id == req.problem_id,
            ProblemProgress.user_id == current_user.id,
        )
    )
    prog = prog_q.scalar_one_or_none()
    if not prog:
        prog = ProblemProgress(problem_id=req.problem_id, user_id=current_user.id)
        db.add(prog)

    prog.total_attempts = (prog.total_attempts or 0) + 1
    prog.total_time_secs = (prog.total_time_secs or 0) + req.time_spent_secs
    prog.last_attempted_at = datetime.now(timezone.utc)
    if runner_data.get("is_correct") and not prog.solved_at:
        prog.solved_at = datetime.now(timezone.utc)
        prog.best_solution = req.code

    if not runner_data.get("is_correct") and runner_data.get("stderr"):
        ep = ErrorPattern(
            attempt_id=attempt_id,
            user_id=current_user.id,
            problem_id=req.problem_id,
            error_category=_classify_error(runner_data.get("stderr", "")),
            error_message=runner_data.get("stderr", "")[:1000],
            code_snippet=req.code[:500],
            category=problem.category,
            difficulty=problem.difficulty,
        )
        db.add(ep)

    await db.commit()

    return RunCodeResponse(
        stdout=runner_data.get("stdout", ""),
        stderr=runner_data.get("stderr", ""),
        is_correct=runner_data.get("is_correct", False),
        test_results=runner_data.get("test_results", []),
        execution_time_ms=runner_data.get("exec_time_ms", runner_data.get("execution_time_ms", 0)),
        attempt_id=str(attempt_id),
        mode=req.mode,
    )

@router.get("/problem/{problem_id}", response_model=List[AttemptOut])
async def get_problem_attempts(
    problem_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ProblemAttempt)
        .where(
            ProblemAttempt.problem_id == problem_id,
            ProblemAttempt.user_id == current_user.id,
        )
        .order_by(ProblemAttempt.submitted_at.desc())
        .limit(20)
    )
    rows = result.scalars().all()
    return [AttemptOut(
        id=str(r.id), problem_id=r.problem_id,
        submitted_at=r.submitted_at, attempt_number=r.attempt_number,
        time_spent_secs=r.time_spent_secs, is_correct=r.is_correct,
        is_first_attempt=r.is_first_attempt, error_type=r.error_type,
        error_message=r.error_message, code=r.code,
    ) for r in rows]

_ERROR_MAP = {
    "syntaxerror":    "SyntaxError",
    "typeerror":      "TypeError",
    "indexerror":     "IndexError",
    "keyerror":       "KeyError",
    "valueerror":     "ValueError",
    "attributeerror": "AttributeError",
    "recursionerror": "RecursionError",
    "timeouterror":   "TimeoutError",
    "memoryerror":    "MemoryError",
    "runtimeerror":   "RuntimeError",
}

def _classify_error(stderr: str) -> str:
    if not stderr:
        return "WrongAnswer"
    s = stderr.lower()
    for key, val in _ERROR_MAP.items():
        if key in s:
            return val
    return "Other"
