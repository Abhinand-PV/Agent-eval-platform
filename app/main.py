import pathlib
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.instrumentation  # noqa: F401 - triggers OTel setup on import
from app.database import get_session, init_db
from app.models import EvalTask, EvalResult, AgentEndpoint
from app.evaluator import run_evaluation

STATIC_DIR = pathlib.Path(__file__).parent / "static"

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization failed: {e}")
    yield

app = FastAPI(title="Agent Eval Platform", lifespan=lifespan)

# Serve static assets (CSS / JS)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/", include_in_schema=False)
async def root():
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/health")
async def health():
    return {"status": "ok"}


class AgentHealthCheck(BaseModel):
    agent_id: int


@app.post("/agents/check-health", summary="Test if an external agent endpoint is reachable")
async def check_agent_health(body: AgentHealthCheck, session: AsyncSession = Depends(get_session)):
    """Ping a registered agent's endpoint to verify it's online."""
    result = await session.execute(
        select(AgentEndpoint).where(AgentEndpoint.id == body.agent_id)
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent with id {body.agent_id} not found.")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(agent.endpoint_url)
            return {"status": "live", "http_status": resp.status_code}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Agent unreachable: {str(e)}")
class TaskCreate(BaseModel):
    question: str
    expected_answer: str
    required_tools: list[str] = []


class TaskResponse(BaseModel):
    id: int
    question: str
    expected_answer: str
    required_tools: list[str]


class AgentCreate(BaseModel):
    name: str
    description: str = ""
    endpoint_url: str


class AgentResponse(BaseModel):
    id: int
    name: str
    description: str
    endpoint_url: str


class EvalRunRequest(BaseModel):
    agent_id: int | None = None

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


@app.get("/tasks", response_model=list[TaskResponse], summary="List all evaluation benchmark tasks")
async def list_tasks(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    """List all benchmark tasks defined on this platform with pagination."""
    result = await session.execute(select(EvalTask).offset(offset).limit(limit))
    tasks = result.scalars().all()
    return [
        TaskResponse(
            id=t.id,
            question=t.question,
            expected_answer=t.expected_answer,
            required_tools=t.required_tools or [],
        )
        for t in tasks
    ]


@app.get("/tasks/{task_id}", response_model=TaskResponse, summary="Get evaluation task by ID")
async def get_task(task_id: int, session: AsyncSession = Depends(get_session)):
    """Retrieve a single evaluation task by ID."""
    result = await session.execute(select(EvalTask).where(EvalTask.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task with id {task_id} not found.")
    return TaskResponse(
        id=task.id,
        question=task.question,
        expected_answer=task.expected_answer,
        required_tools=task.required_tools or [],
    )


@app.delete("/tasks/{task_id}", summary="Delete evaluation task by ID")
async def delete_task(task_id: int, session: AsyncSession = Depends(get_session)):
    """Delete an evaluation task by ID."""
    result = await session.execute(select(EvalTask).where(EvalTask.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task with id {task_id} not found.")
    await session.delete(task)
    await session.commit()
    return {"status": "success", "message": f"Task {task_id} deleted successfully."}


@app.post("/agents", response_model=AgentResponse, summary="Register an external agent")
async def register_agent(agent: AgentCreate, session: AsyncSession = Depends(get_session)):
    """Register your own agent endpoint. The platform will POST {\"question\": \"...\"} to your URL
    and expect a JSON response with an \"answer\" or \"output\" field."""
    db_agent = AgentEndpoint(
        name=agent.name,
        description=agent.description,
        endpoint_url=agent.endpoint_url,
    )
    session.add(db_agent)
    await session.commit()
    await session.refresh(db_agent)
    return AgentResponse(
        id=db_agent.id,
        name=db_agent.name,
        description=db_agent.description or "",
        endpoint_url=db_agent.endpoint_url,
    )


@app.get("/agents", response_model=list[AgentResponse], summary="List all registered agents")
async def list_agents(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    """List all agents that have been registered on this platform with pagination."""
    result = await session.execute(select(AgentEndpoint).offset(offset).limit(limit))
    agents = result.scalars().all()
    return [
        AgentResponse(
            id=a.id,
            name=a.name,
            description=a.description or "",
            endpoint_url=a.endpoint_url,
        )
        for a in agents
    ]


@app.post("/evaluations/run", summary="Run evaluation against all tasks")
async def trigger_evaluation(
    body: EvalRunRequest = EvalRunRequest(),
    session: AsyncSession = Depends(get_session),
):
    """Run evaluations against all saved tasks.
    - If **agent_id** is provided, your registered external agent endpoint is called.
    - If omitted, the platform's built-in internal agent runs instead.
    """
    endpoint_url = None
    if body.agent_id is not None:
        result = await session.execute(
            select(AgentEndpoint).where(AgentEndpoint.id == body.agent_id)
        )
        db_agent = result.scalar_one_or_none()
        if db_agent is None:
            raise HTTPException(status_code=404, detail=f"Agent with id {body.agent_id} not found.")
        endpoint_url = db_agent.endpoint_url

    results = await run_evaluation(session, endpoint_url=endpoint_url)
    return {"status": "completed", "results": results}


@app.get("/evaluations", summary="List historical evaluation results")
async def list_evaluations(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    """Retrieve all historical evaluation run records with pagination."""
    result = await session.execute(
        select(EvalResult).order_by(EvalResult.id.desc()).offset(offset).limit(limit)
    )
    evals = result.scalars().all()
    return [
        {
            "id": e.id,
            "task_id": e.task_id,
            "agent_output": e.agent_output,
            "scores": e.scores or {},
            "latency_ms": e.latency_ms or 0,
            "token_count": e.token_count or 0,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in evals
    ]


@app.get("/evaluations/summary", summary="Get aggregate benchmark evaluation metrics")
async def get_evaluations_summary(session: AsyncSession = Depends(get_session)):
    """Compute platform-wide aggregate performance metrics across all evaluations."""
    result = await session.execute(select(EvalResult))
    evals = result.scalars().all()
    total = len(evals)
    if total == 0:
        return {
            "total_evaluations": 0,
            "avg_correctness": 0.0,
            "avg_hallucination_rate": 0.0,
            "avg_latency_ms": 0.0,
            "total_tokens": 0,
        }

    correctness_scores = [
        e.scores.get("correctness", 0.0) for e in evals if e.scores and "correctness" in e.scores
    ]
    hallucination_rates = [
        e.scores.get("hallucination_rate", 0.0) for e in evals if e.scores and "hallucination_rate" in e.scores
    ]
    latencies = [e.latency_ms or 0 for e in evals]
    tokens = [e.token_count or 0 for e in evals]

    return {
        "total_evaluations": total,
        "avg_correctness": round(sum(correctness_scores) / len(correctness_scores), 4) if correctness_scores else 0.0,
        "avg_hallucination_rate": round(sum(hallucination_rates) / len(hallucination_rates), 4) if hallucination_rates else 0.0,
        "avg_latency_ms": round(sum(latencies) / total, 2),
        "total_tokens": sum(tokens),
    }