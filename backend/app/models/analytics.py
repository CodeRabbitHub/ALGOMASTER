from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP, JSON, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base
import uuid

SENTINEL_UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")

class AIInsight(Base):
    __tablename__ = "ai_insights"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id      = Column(UUID(as_uuid=True), nullable=False, index=True, default=SENTINEL_UUID)
    generated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    insight_type = Column(String(50), nullable=False)
    content      = Column(Text, nullable=False)
    input_context = Column(JSON, default=dict)
    tokens_used  = Column(Integer, default=0)
    model        = Column(String(50), default="gpt-4o")

class LearningMilestone(Base):
    __tablename__ = "learning_milestones"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id        = Column(UUID(as_uuid=True), nullable=False, index=True, default=SENTINEL_UUID)
    achieved_at    = Column(TIMESTAMP(timezone=True), server_default=func.now())
    milestone_type = Column(String(100), nullable=False)
    description    = Column(Text, nullable=False)
    extra_data     = Column("metadata", JSON, default=dict)

class TopicMastery(Base):
    __tablename__ = "topic_mastery"

    category       = Column(String(100), primary_key=True)
    user_id        = Column(UUID(as_uuid=True), primary_key=True, default=SENTINEL_UUID)
    total_problems = Column(Integer, default=0)
    solved         = Column(Integer, default=0)
    easy_solved    = Column(Integer, default=0)
    medium_solved  = Column(Integer, default=0)
    hard_solved    = Column(Integer, default=0)
    avg_attempts   = Column(Float, default=0.0)
    avg_time_secs  = Column(Integer, default=0)
    struggle_index = Column(Float, default=0.0)
    mastery_score  = Column(Float, default=0.0)
    last_updated   = Column(TIMESTAMP(timezone=True), server_default=func.now())
