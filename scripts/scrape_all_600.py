"""
AlgoMaster 600 — Full Problem Scraper
======================================
Fetches all 600 problem pages, extracts:
  - title, difficulty, topics, companies
  - description (Lexical JSON → markdown)
  - constraints (extracted from description)
  - hints
  - inputParams (parameter names + types)
  - testCasesInput / testCasesOutput (10 cases each)
  - externalLink (LeetCode URL)
  - outputType

Saves to: scraped_problems.json
Then run: docker exec algomaster-backend-1 python /app/import_scraped.py

Usage:
  pip install requests beautifulsoup4
  python scrape_all_600.py
"""

import json
import re
import time
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ── Config ────────────────────────────────────────────────────────────────────
URLS_FILE = Path(__file__).parent / "algomaster_600_urls.txt"
OUTPUT_FILE = Path(__file__).parent / "scraped_problems.json"
DELAY_SECONDS = 0.5          # polite delay between requests
BATCH_LOG_EVERY = 10         # print progress every N problems
SESSION_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

# ── Lexical JSON → Markdown ───────────────────────────────────────────────────
FORMAT_CODE   = 16
FORMAT_BOLD   = 1
FORMAT_ITALIC = 2
FORMAT_STRIKE = 4

def lex_node_to_md(node):
    """Recursively convert a Lexical editor node to markdown text."""
    if node is None:
        return ""

    ntype = node.get("type", "")

    if ntype == "text":
        text = node.get("text", "")
        fmt  = node.get("format", 0)
        if fmt & FORMAT_CODE:
            text = f"`{text}`"
        else:
            if fmt & FORMAT_BOLD:
                text = f"**{text}**"
            if fmt & FORMAT_ITALIC:
                text = f"*{text}*"
            if fmt & FORMAT_STRIKE:
                text = f"~~{text}~~"
        return text

    if ntype == "linebreak":
        return "\n"

    children_md = "".join(lex_node_to_md(c) for c in node.get("children", []))

    if ntype in ("paragraph", "root"):
        return children_md + "\n"
    if ntype == "heading":
        level = node.get("tag", "h3").lstrip("h") or "3"
        return "#" * int(level) + " " + children_md + "\n"
    if ntype == "list":
        return children_md
    if ntype == "listitem":
        indent = "  " * max(0, node.get("indent", 0))
        return f"{indent}- {children_md.rstrip()}\n"
    if ntype == "quote":
        return "> " + children_md.strip() + "\n"
    if ntype == "code":
        lang = node.get("language", "")
        return f"```{lang}\n{children_md}```\n"
    if ntype == "link":
        url = node.get("url", "")
        return f"[{children_md.strip()}]({url})"

    return children_md


def lexical_to_markdown(lexical_obj):
    """Convert a full Lexical editor JSON object to a markdown string."""
    if not lexical_obj:
        return ""
    root = lexical_obj.get("root", lexical_obj)
    return lex_node_to_md(root).strip()


# ── Constraint extraction ─────────────────────────────────────────────────────
def extract_constraints(markdown_text):
    """Pull the Constraints section out of the full description markdown."""
    lines = markdown_text.splitlines()
    in_constraints = False
    constraint_lines = []
    for line in lines:
        stripped = line.strip()
        if re.match(r"^#+\s*Constraints?\s*$", stripped, re.IGNORECASE) or stripped.lower() == "constraints:":
            in_constraints = True
            continue
        if in_constraints:
            # Stop at the next heading or blank section
            if re.match(r"^#+\s+", stripped) and stripped.lower() not in ("", "constraints", "constraints:"):
                break
            if stripped:
                constraint_lines.append(stripped.lstrip("- "))
    return "\n".join(constraint_lines)


# ── RSC Payload Parser ────────────────────────────────────────────────────────
_PUSH_RE = re.compile(r'self\.__next_f\.push\(\[1,"(.+?)"\]\)\s*$', re.DOTALL)

def extract_fields_from_html(html: str, slug: str):
    """
    Parse Next.js RSC flight data from the page HTML and return the
    codingPracticeBlock fields dict, or None if not found.
    """
    soup = BeautifulSoup(html, "html.parser")
    scripts = [s.string or "" for s in soup.find_all("script")]

    # Find the script chunk that has codingPracticeBlock
    target_chunk = None
    for s in scripts:
        if "codingPracticeBlock" in s:
            target_chunk = s
            break

    if not target_chunk:
        return None

    # Extract the inner JSON-encoded string from self.__next_f.push([1,"..."])
    m = _PUSH_RE.search(target_chunk)
    if not m:
        return None

    try:
        # The content is a JSON-encoded string (escape sequences, etc.)
        decoded = json.loads('"' + m.group(1) + '"')
    except json.JSONDecodeError:
        # Fallback: try treating it as raw string
        decoded = m.group(1)

    # Locate the codingPracticeBlock fields object
    bt_idx = decoded.find('"blockType":"codingPracticeBlock"')
    if bt_idx < 0:
        return None

    fields_marker = '"fields":{'
    fields_idx = decoded.rfind(fields_marker, 0, bt_idx)
    if fields_idx < 0:
        return None

    start = fields_idx + len('"fields":')

    # Brace-match to find the end of the fields object
    depth = 0
    end = start
    for i in range(start, len(decoded)):
        ch = decoded[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                end = i
                break

    try:
        fields = json.loads(decoded[start:end + 1])
    except json.JSONDecodeError as e:
        print(f"  [WARN] JSON parse error for {slug}: {e}")
        return None

    return fields


# ── Test Case Builder ─────────────────────────────────────────────────────────
def build_test_cases(fields):
    """
    Convert testCasesInput / testCasesOutput multiline strings into
    a list of {"input": "...", "expected_output": "..."} dicts.
    """
    raw_in  = (fields.get("testCasesInput")  or "").strip()
    raw_out = (fields.get("testCasesOutput") or "").strip()
    if not raw_in:
        return []

    # Filter blank separator lines — AlgoMaster puts blank lines between entries
    inputs  = [l.strip() for l in raw_in.splitlines()  if l.strip()]
    outputs = [l.strip() for l in raw_out.splitlines() if l.strip()] if raw_out else []

    cases = []
    for i, inp in enumerate(inputs):
        cases.append({
            "input":           inp,
            "expected_output": outputs[i] if i < len(outputs) else "",
        })
    return cases


# ── Hint Extractor ────────────────────────────────────────────────────────────
def extract_hints(fields):
    hints_raw = fields.get("hints") or []
    hints = []
    for h in hints_raw:
        hint_lex = h.get("hint") or {}
        hint_md  = lexical_to_markdown(hint_lex)
        if hint_md:
            hints.append(hint_md)
    return hints


# ── Main scraper ──────────────────────────────────────────────────────────────
def scrape_problem(session, url: str):
    slug = url.split("/dsa/")[1].split("?")[0]
    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        return {"slug": slug, "error": str(e), "_scraped": False}

    fields = extract_fields_from_html(resp.text, slug)
    if not fields:
        return {"slug": slug, "error": "fields not found (login-gated?)", "_scraped": False}

    # Convert description Lexical → markdown
    full_desc_md = lexical_to_markdown(fields.get("description") or {})
    constraints  = extract_constraints(full_desc_md)

    # Topics → tags
    topics = fields.get("topics") or []

    return {
        "slug":             slug,
        "title":            fields.get("title", ""),
        "difficulty":       fields.get("difficulty", ""),
        "tags":             topics,
        "companies":        fields.get("companies") or [],
        "description":      full_desc_md,
        "constraints":      constraints,
        "hints":            extract_hints(fields),
        "input_params":     fields.get("inputParams") or [],
        "output_type":      fields.get("outputType", ""),
        "test_cases":       build_test_cases(fields),
        "external_link":    fields.get("externalLink", ""),
        "similar_questions": fields.get("similarQuestions") or [],
        "_scraped":         True,
    }


def main():
    if not URLS_FILE.exists():
        print(f"ERROR: {URLS_FILE} not found.")
        sys.exit(1)

    urls = [u.strip() for u in URLS_FILE.read_text().splitlines() if u.strip()]
    print(f"Scraping {len(urls)} problems...")

    # Load existing results so we can resume after interruption
    existing = {}
    if OUTPUT_FILE.exists():
        try:
            existing = {p["slug"]: p for p in json.loads(OUTPUT_FILE.read_text())}
            already_done = sum(1 for p in existing.values() if p.get("_scraped"))
            print(f"Resuming — {already_done}/{len(existing)} already scraped.")
        except Exception:
            pass

    session = requests.Session()
    session.headers.update(SESSION_HEADERS)

    results = dict(existing)
    success = sum(1 for p in results.values() if p.get("_scraped"))
    failed  = 0

    for i, url in enumerate(urls, 1):
        slug = url.split("/dsa/")[1].split("?")[0]

        # Skip already-scraped successes
        if results.get(slug, {}).get("_scraped"):
            continue

        data = scrape_problem(session, url)
        results[slug] = data

        if data.get("_scraped"):
            success += 1
        else:
            failed += 1
            print(f"  [SKIP] {slug}: {data.get('error')}")

        time.sleep(3)  # be polite — 3s between requests

        if i % BATCH_LOG_EVERY == 0 or i == len(urls):
            print(f"  [{i}/{len(urls)}] scraped={success} skipped={failed}")
            # Save checkpoint after every batch
            OUTPUT_FILE.write_text(
                json.dumps(list(results.values()), indent=2, ensure_ascii=False),
                encoding="utf-8"
            )

        time.sleep(DELAY_SECONDS)

    # Final save
    OUTPUT_FILE.write_text(
        json.dumps(list(results.values()), indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"\nDone! {success} scraped, {failed} skipped.")
    print(f"Output: {OUTPUT_FILE}")
    print(f"\nNext step: copy import_scraped.py to backend/ then run:")
    print(f"  docker exec algomaster-backend-1 python /app/import_scraped.py")


if __name__ == "__main__":
    main()
