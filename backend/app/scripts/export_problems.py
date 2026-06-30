"""
Export all problems from the database to a local JSON file.

The JSON file is the persistent local cache — on fresh Docker restarts the
seed script loads from it instead of hitting LeetCode again.

Usage:
    docker compose exec backend python -m app.scripts.export_problems

The file is saved to /app/data/problems_data.json (mounted from ./backend/data/).
"""

import asyncio
import json
import logging
from pathlib import Path
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.problem import Problem

logger = logging.getLogger(__name__)

DATA_PATH = Path("/app/data/problems_data.json")


async def export_problems(path: Path = DATA_PATH) -> int:
    """
    Export all problems to JSON. Returns count of exported problems.
    Skips problems that still have placeholder descriptions so the file
    only contains real data; on reload those will auto-fetch again.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Problem).order_by(Problem.id))
        problems = result.scalars().all()

    data = []
    for p in problems:
        data.append({
            "id": p.id,
            "slug": p.slug,
            "title": p.title,
            "difficulty": p.difficulty.value if hasattr(p.difficulty, "value") else str(p.difficulty),
            "category": p.category,
            "subcategory": p.subcategory or "",
            "leetcode_url": p.leetcode_url or "",
            "description": p.description or "",
            "constraints": p.constraints or "",
            "starter_code": p.starter_code or "",
            "test_cases": p.test_cases or [],
            "hints": p.hints or [],
            "tags": p.tags or [],
            "is_new": p.is_new or False,
        })

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    populated = sum(1 for p in data if len(p["description"]) > 80)
    logger.info(
        f"[export] Wrote {len(data)} problems to {path} "
        f"({populated} with real descriptions)"
    )
    return len(data)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    count = asyncio.run(export_problems())
    print(f"Exported {count} problems to {DATA_PATH}")
