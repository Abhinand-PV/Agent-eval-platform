from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import run_agent
from app.instrumentation import collect_spans, extract_metrics
from app.scoring import score_correctness, score_tool_use
from app.models import EvalTask, EvalResult


async def run_evaluation(session: AsyncSession) -> list[dict]:
    result_set = await session.execute(select(EvalTask))
    tasks = result_set.scalars().all()

    results = []
    for task in tasks:
        agent_result = run_agent(task.question)
        spans = collect_spans()
        metrics = extract_metrics(spans)

        correctness = score_correctness(
            task.question, task.expected_answer, agent_result["output"]
        )

        # Collect spans again after judge call and discard them
        collect_spans()

        tool_score = score_tool_use(
            task.required_tools or [], metrics["tools_called"]
        )
        scores = {
            "correctness": correctness["correctness"],
            "correctness_rationale": correctness["rationale"],
            "tool_use_success": tool_score["tool_use_success"],
            "missing_tools": tool_score["missing_tools"],
            "cost_usd": metrics["cost_usd"],
            "latency_ms": agent_result["latency_ms"],
            "total_tokens": metrics["total_tokens"],
        }

        eval_result = EvalResult(
            task_id=task.id,
            agent_output=agent_result["output"],
            scores=scores,
            latency_ms=agent_result["latency_ms"],
            token_count=metrics["total_tokens"],
            spans_data=[s for s in spans[:10]],
        )
        session.add(eval_result)
        results.append({
            "task_id": task.id,
            "question": task.question,
            "agent_output": agent_result["output"],
            "scores": scores,
            "metrics": metrics,
    })

    await session.commit()
    return results