"""
LeetCode GraphQL fetcher.
Fetches real problem descriptions, examples, hints, and test cases
from LeetCode's public GraphQL API and stores them in the database.

Usage (one-off run):
    docker compose exec backend python -m app.scripts.fetch_leetcode

Or triggered via the admin API endpoint:
    POST /admin/fetch-leetcode
"""

import asyncio
import re
import json
import logging
from urllib.parse import urlparse
from typing import Optional
import httpx
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.problem import Problem

logger = logging.getLogger(__name__)

# ── LeetCode GraphQL ─────────────────────────────────────────────────────────
LEETCODE_GQL = "https://leetcode.com/graphql"

HEADERS = {
    "Content-Type": "application/json",
    "Referer": "https://leetcode.com",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Origin": "https://leetcode.com",
}

QUERY = """
query questionData($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    questionId
    title
    content
    difficulty
    exampleTestcases
    hints
    topicTags { name }
  }
}
"""


# ── Slug extraction ───────────────────────────────────────────────────────────
def slug_from_url(url: str) -> Optional[str]:
    """Extract the LeetCode slug from a full URL."""
    try:
        path = urlparse(url).path          # /problems/two-sum/
        parts = [p for p in path.split("/") if p]
        if "problems" in parts:
            idx = parts.index("problems")
            if idx + 1 < len(parts):
                return parts[idx + 1]
    except Exception:
        pass
    return None


# ── HTML → clean text ─────────────────────────────────────────────────────────
def html_to_text(html: str) -> str:
    if not html:
        return ""
    h = html
    # Newlines for block-level elements
    h = re.sub(r"<br\s*/?>", "\n", h, flags=re.IGNORECASE)
    h = re.sub(r"</(p|div|li)>", "\n", h, flags=re.IGNORECASE)
    h = re.sub(r"<(p|div)[^>]*>", "\n", h, flags=re.IGNORECASE)
    # Code blocks
    h = re.sub(r"<pre[^>]*>", "\n```\n", h, flags=re.IGNORECASE)
    h = re.sub(r"</pre>", "\n```\n", h, flags=re.IGNORECASE)
    h = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", h, flags=re.DOTALL | re.IGNORECASE)
    # Bold / italic
    h = re.sub(r"<strong[^>]*>(.*?)</strong>", r"**\1**", h, flags=re.DOTALL | re.IGNORECASE)
    h = re.sub(r"<em[^>]*>(.*?)</em>", r"*\1*", h, flags=re.DOTALL | re.IGNORECASE)
    # Strip remaining tags
    h = re.sub(r"<[^>]+>", "", h)
    # Decode common entities
    entities = {
        "&nbsp;": " ", "&lt;": "<", "&gt;": ">", "&amp;": "&",
        "&quot;": '"', "&#39;": "'", "&le;": "≤", "&ge;": "≥",
        "&minus;": "−", "&times;": "×",
    }
    for ent, char in entities.items():
        h = h.replace(ent, char)
    # Collapse excessive whitespace / blank lines
    h = re.sub(r" {2,}", " ", h)
    h = re.sub(r"\n{3,}", "\n\n", h)
    return h.strip()


# ── Parse constraints from HTML ──────────────────────────────────────────────
def parse_constraints(html: str) -> str:
    """
    Extract the Constraints section from LeetCode HTML.
    Returns a newline-separated string of constraint items.
    """
    if not html:
        return ""
    # LeetCode format: <p><strong>Constraints:</strong></p>\n<ul><li>...</li></ul>
    match = re.search(
        r"<strong[^>]*>Constraints:</strong>.*?</p>\s*<ul[^>]*>(.*?)</ul>",
        html, re.DOTALL | re.IGNORECASE
    )
    if not match:
        # Alternate: constraints in same <p> block
        match = re.search(
            r"Constraints:</strong>\s*</p>\s*<ul[^>]*>(.*?)</ul>",
            html, re.DOTALL | re.IGNORECASE
        )
    if match:
        items_html = match.group(1)
        items = re.findall(r"<li[^>]*>(.*?)</li>", items_html, re.DOTALL | re.IGNORECASE)
        lines = [html_to_text(item).strip() for item in items if item.strip()]
        return "\n".join(lines)
    return ""


# ── Parse examples from HTML ─────────────────────────────────────────────────
def parse_examples(html: str, example_inputs: str = "") -> list:
    """
    Extract structured examples from LeetCode HTML content.
    Returns list of {input, expected_output, explanation}.
    """
    if not html:
        return []

    examples = []

    # LeetCode wraps examples in <pre> blocks
    pre_blocks = re.findall(r"<pre>(.*?)</pre>", html, re.DOTALL | re.IGNORECASE)

    for block in pre_blocks:
        # Strip HTML tags while preserving newlines
        clean = re.sub(r"<strong[^>]*>", "", block)
        clean = re.sub(r"</strong>", "", clean)
        clean = re.sub(r"<[^>]+>", "", clean)
        # Decode entities
        clean = (clean.replace("&nbsp;", " ").replace("&lt;", "<")
                      .replace("&gt;", ">").replace("&amp;", "&")
                      .replace("&#39;", "'").replace("&quot;", '"'))
        clean = clean.strip()

        # Match Input / Output / Explanation
        inp = re.search(r"Input:\s*(.+?)(?=\nOutput:|\Z)", clean, re.DOTALL)
        out = re.search(r"Output:\s*(.+?)(?=\nExplanation:|\nInput:|\Z)", clean, re.DOTALL)
        exp = re.search(r"Explanation:\s*(.+?)$", clean, re.DOTALL)

        if inp and out:
            examples.append({
                "input": inp.group(1).strip(),
                "expected_output": out.group(1).strip(),
                "explanation": exp.group(1).strip() if exp else "",
            })

    # Fallback: if no <pre> blocks parsed, use exampleTestcases
    if not examples and example_inputs:
        lines = [l.strip() for l in example_inputs.strip().split("\n") if l.strip()]
        for i, line in enumerate(lines):
            examples.append({
                "input": line,
                "expected_output": "",
                "explanation": "",
            })

    return examples


# Sentinel returned when a problem exists but has no public content (Premium)
_PREMIUM = {"__premium__": True}


# ── Fetch single problem ──────────────────────────────────────────────────────
async def fetch_problem_data(slug: str, client: httpx.AsyncClient, attempt: int = 1) -> Optional[dict]:
    """
    Call LeetCode GraphQL and return raw question data.
    Returns:
      dict with content  → real problem
      _PREMIUM sentinel  → problem exists but is premium / no public content
      None               → network / server error (retryable)
    """
    try:
        resp = await client.post(
            LEETCODE_GQL,
            json={"query": QUERY, "variables": {"titleSlug": slug}},
            headers=HEADERS,
            timeout=20,
        )
        if resp.status_code == 200:
            data = resp.json()
            q = data.get("data", {}).get("question")
            if q and q.get("content"):
                return q
            # 200 but empty → premium / locked / doesn't exist
            logger.info(f"[LeetCode] No public content for '{slug}' (premium or unavailable)")
            return _PREMIUM
        elif resp.status_code == 429:
            # Rate limited — exponential backoff, up to 3 attempts
            if attempt <= 3:
                wait = 10 * attempt  # 10s, 20s, 30s
                logger.warning(f"[LeetCode] Rate limited on '{slug}', waiting {wait}s (attempt {attempt}/3)")
                await asyncio.sleep(wait)
                return await fetch_problem_data(slug, client, attempt + 1)
            logger.error(f"[LeetCode] Gave up on '{slug}' after 3 rate-limit retries")
        else:
            logger.warning(f"[LeetCode] HTTP {resp.status_code} for slug='{slug}'")
    except Exception as e:
        logger.error(f"[LeetCode] Error fetching '{slug}': {e}")
    return None


# ── Update single problem in DB ───────────────────────────────────────────────
async def enrich_problem(problem: Problem, client: httpx.AsyncClient, db) -> str:
    """
    Fetch from LeetCode and update the problem row.
    Returns: 'ok' | 'premium' | 'error'
    """
    slug = slug_from_url(problem.leetcode_url or "")
    if not slug:
        return "error"

    data = await fetch_problem_data(slug, client)

    if data is _PREMIUM:
        # Mark as premium so UI can distinguish from retryable errors
        problem.description = (
            f"**Premium Problem** — '{problem.title}' requires a LeetCode Premium "
            f"subscription and is not publicly available via the API.\n\n"
            f"[Open on LeetCode]({problem.leetcode_url})"
        )
        return "premium"

    if data is None:
        return "error"

    html = data.get("content", "")
    example_inputs = data.get("exampleTestcases", "")
    hints_raw = data.get("hints", [])
    topic_tags = [t.get("name", "") for t in (data.get("topicTags") or []) if t.get("name")]

    description = html_to_text(html)
    examples = parse_examples(html, example_inputs)
    hints = [html_to_text(h) for h in hints_raw if h]
    constraints = parse_constraints(html)

    if len(description) > 50:
        problem.description = description
        problem.test_cases = examples
        problem.hints = hints
        problem.tags = topic_tags
        problem.constraints = constraints
        return "ok"

    return "premium"


# ── Bulk fetch all problems ───────────────────────────────────────────────────
_fetch_progress = {
    "total": 0, "done": 0, "errors": 0, "premium": 0,
    "running": False, "failed_slugs": [],
}


async def fetch_all(batch_size: int = 5, delay: float = 1.5):
    """
    Fetch descriptions for all problems that still have placeholder text.
    Runs with rate-limiting to avoid hitting LeetCode's limits.
    """
    global _fetch_progress

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Problem))
        all_problems = result.scalars().all()

    # Filter: only problems with placeholder / short descriptions
    # and deduplicate by slug so we don't hammer the same URL twice
    seen_slugs: dict[str, Problem] = {}
    needs_fetch = []
    for p in all_problems:
        slug = slug_from_url(p.leetcode_url or "")
        if not slug:
            continue
        is_placeholder = (
            not p.description
            or "TODO" in p.description
            or p.description.startswith("Solve the '")
            or len(p.description) < 80
        )
        if is_placeholder and slug not in seen_slugs:
            seen_slugs[slug] = p
            needs_fetch.append(p)

    _fetch_progress.update({
        "total": len(needs_fetch), "done": 0, "errors": 0,
        "premium": 0, "running": True, "failed_slugs": [],
    })
    logger.info(f"[LeetCode] Fetching {len(needs_fetch)} problems...")

    async with httpx.AsyncClient() as client:
        for i in range(0, len(needs_fetch), batch_size):
            batch = needs_fetch[i: i + batch_size]
            async with AsyncSessionLocal() as db:
                for p in batch:
                    # Re-fetch the problem row in this session
                    result = await db.execute(select(Problem).where(Problem.id == p.id))
                    prob = result.scalar_one_or_none()
                    if prob is None:
                        continue

                    slug = slug_from_url(prob.leetcode_url or "")
                    status = await enrich_problem(prob, client, db)

                    # Update all duplicate-URL problems with same data
                    if status in ("ok", "premium"):
                        dupes = await db.execute(
                            select(Problem).where(
                                Problem.leetcode_url == prob.leetcode_url,
                                Problem.id != prob.id,
                            )
                        )
                        for dup in dupes.scalars().all():
                            dup.description = prob.description
                            dup.test_cases = prob.test_cases
                            dup.hints = prob.hints
                            dup.tags = prob.tags
                            dup.constraints = prob.constraints

                    if status == "ok":
                        _fetch_progress["done"] += 1
                        logger.info(f"[LeetCode] ✓ {slug} ({_fetch_progress['done']}/{_fetch_progress['total']})")
                    elif status == "premium":
                        _fetch_progress["premium"] += 1
                        logger.info(f"[LeetCode] 🔒 {slug} (premium/unavailable)")
                    else:
                        _fetch_progress["errors"] += 1
                        _fetch_progress["failed_slugs"].append(slug)
                        logger.warning(f"[LeetCode] ✗ {slug} (error — retryable)")

                    await asyncio.sleep(delay)

                await db.commit()

    _fetch_progress["running"] = False
    logger.info(f"[LeetCode] Done. {_fetch_progress['done']} fetched, {_fetch_progress['errors']} errors.")

    # Auto-export to local JSON cache so fresh Docker restarts skip LeetCode fetch
    try:
        from app.scripts.export_problems import export_problems
        count = await export_problems()
        logger.info(f"[LeetCode] Auto-exported {count} problems to local JSON cache.")
        _fetch_progress["exported"] = count
    except Exception as e:
        logger.warning(f"[LeetCode] Auto-export failed (non-fatal): {e}")

    return _fetch_progress.copy()


def get_progress() -> dict:
    return _fetch_progress.copy()


# ── Standalone entry point ────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    batch = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    delay = float(sys.argv[2]) if len(sys.argv) > 2 else 1.5
    result = asyncio.run(fetch_all(batch_size=batch, delay=delay))
    print(json.dumps(result, indent=2))
