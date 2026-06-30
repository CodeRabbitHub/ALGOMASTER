from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

class ProblemOut(BaseModel):
    id: int
    slug: str
    title: str
    difficulty: str
    category: str
    subcategory: Optional[str] = None
    leetcode_url: Optional[str] = None
    description: str = ""
    constraints: str = ""
    starter_code: str = ""
    test_cases: List[Any] = []
    hints: List[Any] = []
    tags: List[str] = []
    is_new: bool = False

    model_config = {"from_attributes": True}

class ProgressOut(BaseModel):
    problem_id: int
    solved_at: Optional[datetime] = None
    total_attempts: int = 0
    total_time_secs: int = 0
    is_starred: bool = False
    confidence: int = 0
    notes: str = ""
    best_solution: str = ""
    last_attempted_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class ProgressUpdate(BaseModel):
    is_starred: Optional[bool] = None
    confidence: Optional[int] = None
    notes: Optional[str] = None
    best_solution: Optional[str] = None

class RunCodeRequest(BaseModel):
    problem_id: int
    code: str
    time_spent_secs: int = 0
    mode: str = "run"          # "run" → first 3 cases, "submit" → all cases
    session_id: Optional[str] = None

class RunCodeResponse(BaseModel):
    stdout: str
    stderr: str
    is_correct: bool
    test_results: List[Any] = []
    execution_time_ms: int = 0
    attempt_id: Optional[str] = None
    mode: str = "run"
