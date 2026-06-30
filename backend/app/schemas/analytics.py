from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from datetime import datetime, date

class AttemptOut(BaseModel):
    id: str
    problem_id: int
    submitted_at: datetime
    attempt_number: int
    time_spent_secs: int
    is_correct: bool
    is_first_attempt: bool
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    code: Optional[str] = None

    model_config = {"from_attributes": True}

class DailyStatOut(BaseModel):
    day: date
    total_attempts: int = 0
    solved: int = 0
    first_attempt_wins: int = 0
    problems_touched: int = 0
    total_time_secs: int = 0
    errors_count: int = 0

class TopicMasteryOut(BaseModel):
    category: str
    total_problems: int
    solved: int
    easy_solved: int
    medium_solved: int
    hard_solved: int
    avg_attempts: float
    avg_time_secs: int
    struggle_index: float
    mastery_score: float

    model_config = {"from_attributes": True}

class OverviewStatsOut(BaseModel):
    total_problems: int
    total_solved: int
    easy_solved: int
    medium_solved: int
    hard_solved: int
    total_attempts: int
    total_time_secs: int
    first_attempt_success_rate: float
    current_streak: int
    longest_streak: int
    avg_attempts_per_problem: float
    solve_velocity_7d: float  # problems solved per day (last 7 days)
    solve_velocity_30d: float

class AIInsightOut(BaseModel):
    id: str
    generated_at: datetime
    insight_type: str
    content: str
    tokens_used: int
    model: str

    model_config = {"from_attributes": True}

class AIInsightRequest(BaseModel):
    insight_type: str  # weekly_report | study_plan | code_review | chat | mistake_analysis | hint | mistake_explain
    message: Optional[str] = None        # for chat
    code: Optional[str] = None           # for code_review / mistake_explain
    problem_id: Optional[int] = None     # for hint / code_review / mistake_explain
    failed_cases: Optional[List[Any]] = None  # for mistake_explain

class MilestoneOut(BaseModel):
    id: str
    achieved_at: datetime
    milestone_type: str
    description: str
    metadata: Dict[str, Any] = {}

    model_config = {"from_attributes": True}

class ErrorPatternOut(BaseModel):
    error_category: str
    count: int
    recent_problems: List[str] = []
    trend: str = "stable"  # improving | worsening | stable
