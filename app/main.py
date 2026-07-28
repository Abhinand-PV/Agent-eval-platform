from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.instrumentation  # noqa: F401 - triggers OTel setup on import
from app.database import get_session, init_db
from app.models import EvalTask, EvalResult, AgentEndpoint
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

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

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
async def list_agents(session: AsyncSession = Depends(get_session)):
    """List all agents that have been registered on this platform."""
    result = await session.execute(select(AgentEndpoint))
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
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail=f"Agent with id {body.agent_id} not found.")
        endpoint_url = db_agent.endpoint_url

    results = await run_evaluation(session, endpoint_url=endpoint_url)
    return {"status": "completed", "results": results}