from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class EvalTask(Base):
    __tablename__ = "eval_tasks"

    id = Column(Integer, primary_key=True)
    question = Column(String, nullable=False)
    expected_answer = Column(String, nullable=False)
    required_tools = Column(JSON, default=list)
    created_at = Column(DateTime, server_default=func.now())
class EvalResult(Base):
    __tablename__ = "eval_results"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, nullable=False)
    agent_output = Column(String)
    scores = Column(JSON)
    latency_ms = Column(Integer)
    token_count = Column(Integer)
    spans_data = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())