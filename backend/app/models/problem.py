from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP, JSON, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base
import enum, uuid

SENTINEL_UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")

class DifficultyEnum(str, enum.Enum):
    Easy = "Easy"
    Medium = "Medium"
    Hard = "Hard"

class Problem(Base):
    __tablename__ = "problems"

    id           = Column(Integer, primary_key=True, index=True)
    slug         = Column(String(200), unique=True, nullable=False, index=True)
    title        = Column(String(300), nullable=False)
    difficulty   = Column(SAEnum(DifficultyEnum, name="difficulty_enum", create_type=False), nullable=False)
    category     = Column(String(100), nullable=False, index=True)
    subcategory  = Column(String(100))
    leetcode_url = Column(Text)
    description  = Column(Text, default="")
    starter_code = Column(Text, default="def solution():\n    pass\n")
    test_cases   = Column(JSON, default=list)
    hints        = Column(JSON, default=list)
    tags         = Column(JSON, default=list)   # ["Array", "Hash Table", …]
    constraints  = Column(Text, default="")     # parsed constraints block
    input_params = Column(JSON, default=list)   # [{inputName, inputType}, …]
    output_type  = Column(Text, default="")     # "array", "number", "boolean", etc.
    is_new       = Column(Boolean, default=False)
    created_at   = Column(TIMESTAMP(timezone=True), server_default=func.now())

class ProblemProgress(Base):
    __tablename__ = "problem_progress"

    problem_id        = Column(Integer, primary_key=True)
    user_id           = Column(UUID(as_uuid=True), primary_key=True, default=SENTINEL_UUID)
    first_seen_at     = Column(TIMESTAMP(timezone=True), server_default=func.now())
    solved_at         = Column(TIMESTAMP(timezone=True), nullable=True)
    total_attempts    = Column(Integer, default=0)
    total_time_secs   = Column(Integer, default=0)
    is_starred        = Column(Boolean, default=False)
    confidence        = Column(Integer, default=0)
    notes             = Column(Text, default="")
    best_solution     = Column(Text, default="")
    last_attempted_at = Column(TIMESTAMP(timezone=True), nullable=True)
