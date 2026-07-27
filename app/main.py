from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.instrumentation  # noqa: F401 - triggers OTel setup on import
from app.database import get_session, init_db
from app.models import EvalTask, EvalResult
from app.evaluator import run_evaluation

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization failed: {e}")
    yield

app = FastAPI(title="Agent Eval Platform", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok"}
class TaskCreate(BaseModel):
    question: str
    expected_answer: str
    required_tools: list[str] = []


class TaskResponse(BaseModel):
    id: int
    question: str
    expected_answer: str
    required_tools: list[str]
@app.post("/tasks", response_model=TaskResponse)
async def create_task(task: TaskCreate, session: AsyncSession = Depends(get_session)):
    db_task = EvalTask(
        question=task.question,
        expected_answer=task.expected_answer,
        required_tools=task.required_tools,
    )
    session.add(db_task)
    await session.commit()
    await session.refresh(db_task)
    return TaskResponse(
        id=db_task.id,
        question=db_task.question,
        expected_answer=db_task.expected_answer,
        required_tools=db_task.required_tools or [],
    )


@app.post("/evaluations/run")
async def trigger_evaluation(session: AsyncSession = Depends(get_session)):
    results = await run_evaluation(session)
    return {"status": "completed", "results": results}