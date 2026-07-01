from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


class SelfAssessmentIn(BaseModel):
    problem_id: int

    # Pattern Recognition
    pattern_identified: Optional[str] = None
    time_to_pattern_secs: Optional[int] = None
    pattern_was_correct: Optional[bool] = None

    # Solve phases
    time_to_first_idea_secs: Optional[int] = None
    time_to_algorithm_secs: Optional[int] = None
    total_solve_time_secs: Optional[int] = None
    wrong_approaches: Optional[int] = 0
    hint_used: Optional[bool] = False
    did_panic: Optional[bool] = False

    # Complexity
    complexity_initial_time: Optional[str] = None
    complexity_final_time: Optional[str] = None
    complexity_final_space: Optional[str] = None

    # Coding quality
    compile_attempts: Optional[int] = 1
    bugs_count: Optional[int] = 0
    bug_categories: Optional[List[str]] = []
    debug_time_secs: Optional[int] = None

    # Communication
    communication_score: Optional[int] = Field(None, ge=1, le=10)

    # Edge cases
    edge_cases_checked: Optional[List[str]] = []
    edge_cases_before_coding: Optional[bool] = None

    # Learning
    new_learning: Optional[str] = None

    # Confidence
    confidence_after: Optional[int] = Field(None, ge=1, le=5)

    # Spaced repetition flag
    add_to_review: Optional[bool] = False


class SelfAssessmentOut(BaseModel):
    id: str
    problem_id: int
    assessed_at: datetime
    pattern_identified: Optional[str]
    time_to_pattern_secs: Optional[int]
    pattern_was_correct: Optional[bool]
    complexity_initial_time: Optional[str]
    complexity_final_time: Optional[str]
    complexity_final_space: Optional[str]
    compile_attempts: Optional[int]
    bugs_count: Optional[int]
    bug_categories: Optional[List[str]]
    communication_score: Optional[int]
    edge_cases_checked: Optional[List[str]]
    edge_cases_before_coding: Optional[bool]
    new_learning: Optional[str]
    confidence_after: Optional[int]
    hint_used: Optional[bool]
    wrong_approaches: Optional[int]
    did_panic: Optional[bool]


class ReviewCompleteIn(BaseModel):
    problem_id: int
    quality: int = Field(..., ge=0, le=5)   # SM-2 quality score


class ReviewScheduleOut(BaseModel):
    problem_id: int
    next_review_at: datetime
    interval_days: float
    ease_factor: float
    rep_count: int
    last_score: Optional[int]
    last_reviewed_at: Optional[datetime]
    # Problem details (joined)
    title: Optional[str] = None
    difficulty: Optional[str] = None
    category: Optional[str] = None


class ReviewsAddIn(BaseModel):
    problem_id: int


class MistakeIn(BaseModel):
    problem_id: Optional[int] = None
    category: str
    notes: Optional[str] = None


class MistakeOut(BaseModel):
    id: str
    problem_id: Optional[int]
    occurred_at: datetime
    category: str
    notes: Optional[str]
    # Problem title (joined)
    problem_title: Optional[str] = None


class ContestIn(BaseModel):
    platform: str = "LeetCode"
    contest_name: Optional[str] = None
    contest_date: datetime
    rating: Optional[int] = None
    rating_change: Optional[int] = None
    global_rank: Optional[int] = None
    questions_solved: int = 0
    total_questions: int = 4
    penalty_mins: Optional[int] = None
    notes: Optional[str] = None


class ContestOut(BaseModel):
    id: str
    platform: str
    contest_name: Optional[str]
    contest_date: datetime
    rating: Optional[int]
    rating_change: Optional[int]
    global_rank: Optional[int]
    questions_solved: int
    total_questions: int
    penalty_mins: Optional[int]
    notes: Optional[str]
    created_at: datetime


class DSFluencyIn(BaseModel):
    ratings: dict  # {ds_name: rating (1-5)}


class DSFluencyOut(BaseModel):
    ds_name: str
    rating: int
    last_updated: datetime


class ReadinessScoreOut(BaseModel):
    total_score: float
    label: str
    label_color: str
    dimensions: dict
