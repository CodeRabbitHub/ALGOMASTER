from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
from app.database import get_db
from app.models.problem import Problem
from app.models.user import User
from app.core.deps import require_admin
from app.scripts.fetch_leetcode import (
    fetch_all, enrich_problem, get_progress, slug_from_url
)
import httpx
import os


class ManualUpdateBody(BaseModel):
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    constraints: Optional[str] = None

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.post("/fetch-leetcode")
async def start_bulk_fetch(background_tasks: BackgroundTasks):
    """
    Start fetching real descriptions for all problems from LeetCode.
    Runs in background — poll /admin/fetch-progress to track status.
    """
    progress = get_progress()
    if progress.get("running"):
        return {"status": "already_running", "progress": progress}

    background_tasks.add_task(fetch_all, batch_size=5, delay=1.5)
    return {"status": "started", "message": "Fetching in background. Poll /admin/fetch-progress."}


@router.get("/fetch-progress")
async def fetch_progress():
    """Return current bulk-fetch progress."""
    return get_progress()


@router.post("/fetch-leetcode/{problem_id}")
async def fetch_single(problem_id: int, db: AsyncSession = Depends(get_db)):
    """
    Fetch and store real description for a single problem on demand.
    Called automatically by the frontend when opening a problem with placeholder text.
    """
    result = await db.execute(select(Problem).where(Problem.id == problem_id))
    problem = result.scalar_one_or_none()
    if not problem:
        raise HTTPException(404, "Problem not found")

    slug = slug_from_url(problem.leetcode_url or "")
    if not slug:
        raise HTTPException(400, "No LeetCode URL configured for this problem")

    async with httpx.AsyncClient() as client:
        status = await enrich_problem(problem, client, db)

    if status in ("ok", "premium"):
        await db.commit()
        return {
            "status": status,
            "slug": slug,
            "description_length": len(problem.description or ""),
            "test_cases_count": len(problem.test_cases or []),
            "hints_count": len(problem.hints or []),
            "premium": status == "premium",
        }
    else:
        raise HTTPException(502, f"Could not fetch data for slug '{slug}' from LeetCode (network/rate-limit error)")


@router.get("/problems/no-description")
async def problems_without_description(db: AsyncSession = Depends(get_db)):
    """List all problems that have no real description (placeholder, premium, or empty)."""
    result = await db.execute(select(Problem))
    all_problems = result.scalars().all()
    missing = [
        {
            "id": str(p.id),
            "title": p.title,
            "category": p.category,
            "difficulty": p.difficulty,
            "slug": slug_from_url(p.leetcode_url or ""),
            "leetcode_url": p.leetcode_url,
            "reason": (
                "premium" if p.description and "Premium Problem" in p.description
                else "empty" if not p.description or len(p.description.strip()) == 0
                else "placeholder"
            ),
        }
        for p in all_problems
        if (
            not p.description
            or len(p.description.strip()) < 80
            or p.description.startswith("Solve the '")
            or "Premium Problem" in p.description
        )
    ]
    missing.sort(key=lambda x: (x["category"], x["title"]))
    return {
        "count": len(missing),
        "premium": sum(1 for m in missing if m["reason"] == "premium"),
        "empty_or_placeholder": sum(1 for m in missing if m["reason"] != "premium"),
        "problems": missing,
    }


@router.patch("/problems/{slug}/manual")
async def manual_update_problem(
    slug: str,
    body: ManualUpdateBody,
    db: AsyncSession = Depends(get_db),
):
    """
    Manually set description/tags/constraints for a problem by LeetCode slug.
    Used for premium problems that can't be auto-fetched.
    Updates ALL problems sharing that slug (same LeetCode URL in multiple categories).
    """
    result = await db.execute(select(Problem))
    all_problems = result.scalars().all()
    matched = [p for p in all_problems if slug in (p.leetcode_url or "")]
    if not matched:
        raise HTTPException(404, f"No problem found with slug '{slug}'")

    for p in matched:
        if body.description is not None:
            p.description = body.description.strip()
        if body.tags is not None:
            p.tags = body.tags
        if body.constraints is not None:
            p.constraints = body.constraints.strip()

    await db.commit()
    return {
        "status": "ok",
        "updated": len(matched),
        "slug": slug,
        "titles": [p.title for p in matched],
    }


@router.post("/export-problems")
async def export_problems_endpoint():
    """
    Export all problems from the DB to /app/data/problems_data.json.
    On any future fresh Docker start (wiped volume), the seed loads from
    this file instead of fetching from LeetCode again.
    """
    try:
        from app.scripts.export_problems import export_problems
        count = await export_problems()
        return {
            "status": "ok",
            "exported": count,
            "path": "/app/data/problems_data.json",
            "tip": "Mount ./backend/data/ in docker-compose to persist this file on your host.",
        }
    except Exception as e:
        raise HTTPException(500, f"Export failed: {e}")


@router.get("/export-status")
async def export_status():
    """Check whether a local JSON cache exists and its size."""
    path = "/app/data/problems_data.json"
    exists = os.path.exists(path)
    size = os.path.getsize(path) if exists else 0
    return {
        "exists": exists,
        "path": path,
        "size_bytes": size,
        "size_mb": round(size / 1_048_576, 2) if size else 0,
    }
