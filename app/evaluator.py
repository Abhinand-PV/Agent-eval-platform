from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import run_agent
from app.instrumentation import collect_spans, extract_metrics
from app.models import EvalTask, EvalResult
async def run_evaluation(session: AsyncSession) -> list[dict]:
    """Run the agent against all tasks and store raw results."""
    result_set = await session.execute(select(EvalTask))
    tasks = result_set.scalars().all()

    results = []
    for task in tasks:
        agent_result = run_agent(task.question)
        spans = collect_spans()
        metrics = extract_metrics(spans)

        eval_result = EvalResult(
            task_id=task.id,
            agent_output=agent_result["output"],
            scores=None,
            latency_ms=agent_result["latency_ms"],
            token_count=metrics["total_tokens"],
            spans_data=[s for s in spans[:10]],
        )
        session.add(eval_result)
        results.append({
            "task_id": task.id,
            "question": task.question,
            "agent_output": agent_result["output"],
            "metrics": metrics,
        })

    await session.commit()
    return results