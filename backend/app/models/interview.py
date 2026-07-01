from sqlalchemy import (
    Column, Integer, String, Text, Boolean, TIMESTAMP, JSON,
    SmallInteger, Float
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base
import uuid

SENTINEL_UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")

# ── Patterns users can recognize ─────────────────────────────────────────────
PATTERNS = [
    "Sliding Window", "Two Pointers", "Binary Search", "BFS", "DFS",
    "Backtracking", "Dynamic Programming", "Greedy", "Trie", "Heap / Priority Queue",
    "Prefix Sum", "Monotonic Stack", "Union Find", "Interval Merge",
    "Divide & Conquer", "Topological Sort", "Math", "Bit Manipulation", "Other",
]

# ── Bug categories that can be logged ────────────────────────────────────────
BUG_CATEGORIES = [
    "Off-by-one", "Wrong condition", "Boundary check", "Null / None check",
    "Wrong data structure", "Overflow", "Logic error", "Loop condition",
    "Initialization", "Missing base case", "Wrong return type", "Syntax",
]

# ── Mistake categories (per the framework) ───────────────────────────────────
MISTAKE_CATEGORIES = [
    "Misread the problem", "Wrong algorithm choice", "Missed edge case",
    "Forgot standard technique", "Complexity too high", "Implementation bug",
    "Debugging mistake", "Time management",
]

# ── Edge cases users can check ───────────────────────────────────────────────
EDGE_CASES = [
    "Empty input", "Single element", "Duplicates", "Negative numbers",
    "Sorted array", "Large input / overflow", "Cycles in graph",
    "Disconnected graph", "All same values", "Null / None",
]

# ── Data structures to rate ───────────────────────────────────────────────────
DATA_STRUCTURES = [
    "Array", "String", "HashMap", "HashSet", "Stack", "Queue",
    "Heap", "Linked List", "Binary Tree", "BST", "Graph", "Trie",
    "Deque", "Union Find", "Fenwick Tree", "Segment Tree",
]


class SelfAssessment(Base):
    """Per-problem post-solve self-assessment."""
    __tablename__ = "self_assessments"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id      = Column(UUID(as_uuid=True), nullable=False, index=True, default=SENTINEL_UUID)
    problem_id   = Column(Integer, nullable=False, index=True)
    assessed_at  = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # ── Pattern Recognition ──────────────────────────────────────────────────
    pattern_identified    = Column(String(100), nullable=True)   # e.g. "Sliding Window"
    time_to_pattern_secs  = Column(Integer, nullable=True)       # seconds from session start
    pattern_was_correct   = Column(Boolean, nullable=True)       # did they pick the right one?

    # ── Solve Phase Timings ──────────────────────────────────────────────────
    time_to_first_idea_secs  = Column(Integer, nullable=True)    # seconds to first approach idea
    time_to_algorithm_secs   = Column(Integer, nullable=True)    # seconds to finalize algorithm
    total_solve_time_secs    = Column(Integer, nullable=True)    # total wall-clock time
    wrong_approaches         = Column(SmallInteger, default=0)   # # of dead ends explored
    hint_used                = Column(Boolean, default=False)
    did_panic                = Column(Boolean, default=False)

    # ── Complexity Analysis ──────────────────────────────────────────────────
    complexity_initial_time  = Column(String(30), nullable=True)  # "O(n²)"
    complexity_final_time    = Column(String(30), nullable=True)  # "O(n)"
    complexity_final_space   = Column(String(30), nullable=True)  # "O(n)"

    # ── Coding Quality ───────────────────────────────────────────────────────
    compile_attempts = Column(SmallInteger, default=1)
    bugs_count       = Column(SmallInteger, default=0)
    bug_categories   = Column(JSON, default=list)     # list of strings from BUG_CATEGORIES
    debug_time_secs  = Column(Integer, nullable=True)

    # ── Communication ────────────────────────────────────────────────────────
    communication_score = Column(SmallInteger, nullable=True)  # 1–10

    # ── Edge Cases ───────────────────────────────────────────────────────────
    edge_cases_checked          = Column(JSON, default=list)    # list of strings from EDGE_CASES
    edge_cases_before_coding    = Column(Boolean, nullable=True)

    # ── Learning ─────────────────────────────────────────────────────────────
    new_learning = Column(Text, nullable=True)

    # ── Post-solve Confidence ────────────────────────────────────────────────
    confidence_after = Column(SmallInteger, nullable=True)  # 1–5


class ReviewSchedule(Base):
    """
    Spaced-repetition review schedule using the SM-2 algorithm.
    One row per (user, problem). Updates in-place on each review.
    """
    __tablename__ = "review_schedule"

    problem_id     = Column(Integer, primary_key=True)
    user_id        = Column(UUID(as_uuid=True), primary_key=True, default=SENTINEL_UUID)
    next_review_at = Column(TIMESTAMP(timezone=True), nullable=False)
    interval_days  = Column(Float, default=1.0)   # current SM-2 interval
    ease_factor    = Column(Float, default=2.5)   # SM-2 ease factor (min 1.3)
    rep_count      = Column(Integer, default=0)   # successful repetitions so far
    last_score     = Column(SmallInteger, nullable=True)  # last quality score 0–5
    last_reviewed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    added_at       = Column(TIMESTAMP(timezone=True), server_default=func.now())


class MistakeLog(Base):
    """Categorized mistake log per problem."""
    __tablename__ = "mistake_log"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id     = Column(UUID(as_uuid=True), nullable=False, index=True, default=SENTINEL_UUID)
    problem_id  = Column(Integer, nullable=True, index=True)
    occurred_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    category    = Column(String(100), nullable=False)   # from MISTAKE_CATEGORIES
    notes       = Column(Text, nullable=True)


class ContestLog(Base):
    """Manual log of competitive programming contest results."""
    __tablename__ = "contest_log"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id          = Column(UUID(as_uuid=True), nullable=False, index=True, default=SENTINEL_UUID)
    platform         = Column(String(50), default="LeetCode")
    contest_name     = Column(String(200), nullable=True)
    contest_date     = Column(TIMESTAMP(timezone=True), nullable=False)
    rating           = Column(Integer, nullable=True)
    rating_change    = Column(Integer, nullable=True)   # positive or negative delta
    global_rank      = Column(Integer, nullable=True)
    questions_solved = Column(SmallInteger, default=0)
    total_questions  = Column(SmallInteger, default=4)
    penalty_mins     = Column(Integer, nullable=True)
    notes            = Column(Text, nullable=True)
    created_at       = Column(TIMESTAMP(timezone=True), server_default=func.now())


class DSFluency(Base):
    """Per-user data-structure fluency ratings (1–5)."""
    __tablename__ = "ds_fluency"

    user_id      = Column(UUID(as_uuid=True), primary_key=True, default=SENTINEL_UUID)
    ds_name      = Column(String(100), primary_key=True)
    rating       = Column(SmallInteger, default=1)   # 1–5
    last_updated = Column(TIMESTAMP(timezone=True), server_default=func.now())
