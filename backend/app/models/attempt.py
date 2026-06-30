from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP, JSON, SmallInteger, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base
import uuid

SENTINEL_UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")

class ProblemAttempt(Base):
    __tablename__ = "problem_attempts"

    id               = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)
    user_id          = Column(UUID(as_uuid=True), nullable=False, index=True, default=SENTINEL_UUID)
    problem_id       = Column(Integer, nullable=False, index=True)
    session_id       = Column(UUID(as_uuid=True), nullable=True)
    submitted_at     = Column(TIMESTAMP(timezone=True), server_default=func.now(), primary_key=True, index=True)
    started_at       = Column(TIMESTAMP(timezone=True), server_default=func.now())
    attempt_number   = Column(SmallInteger, default=1)
    time_spent_secs  = Column(Integer, default=0)
    code             = Column(Text, default="")
    is_correct       = Column(Boolean, default=False)
    is_first_attempt = Column(Boolean, default=False)
    error_type       = Column(String(50), nullable=True)
    error_message    = Column(Text, nullable=True)
    stdout           = Column(Text, nullable=True)
    test_results     = Column(JSON, default=list)

class Session(Base):
    __tablename__ = "sessions"

    id                  = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)
    started_at          = Column(TIMESTAMP(timezone=True), server_default=func.now(), primary_key=True)
    ended_at            = Column(TIMESTAMP(timezone=True), nullable=True)
    problems_attempted  = Column(Integer, default=0)
    problems_solved     = Column(Integer, default=0)
    total_time_secs     = Column(Integer, default=0)

class ErrorPattern(Base):
    __tablename__ = "error_patterns"

    id             = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)
    user_id        = Column(UUID(as_uuid=True), nullable=False, index=True, default=SENTINEL_UUID)
    attempt_id     = Column(UUID(as_uuid=True), nullable=True)
    problem_id     = Column(Integer, nullable=False, index=True)
    occurred_at    = Column(TIMESTAMP(timezone=True), server_default=func.now(), primary_key=True)
    error_category = Column(String(50))
    error_message  = Column(Text)
    code_snippet   = Column(Text)
    category       = Column(String(100))
    difficulty     = Column(String(10))
    ai_diagnosis   = Column(Text, nullable=True)
