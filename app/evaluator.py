import time
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import run_agent
from app.instrumentation import collect_spans, extract_metrics
from app.scoring import score_correctness, score_tool_use, score_hallucination
from app.models import EvalTask, EvalResult

def extract_tool_outputs(messages) -> list[str]:
    """Pull the content from tool-type messages in the agent's history."""
    outputs = []
    for msg in messages:
        if hasattr(msg, "type") and msg.type == "tool":
            outputs.append(msg.content)
    return outputs


async def call_external_agent(endpoint_url: str, question: str) -> dict:
    """Call a user-registered external agent endpoint and return a normalized result dict."""
    payload = {"question": question}
    start_time = time.perf_counter()
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(endpoint_url, json=payload)
        response.raise_for_status()
        data = response.json()
    end_time = time.perf_counter()
    latency_ms = int((end_time - start_time) * 1000)

    # Accept either 'answer' or 'output' as the response key
    output = data.get("answer") or data.get("output") or str(data)
    return {
        "output": output,
        "messages": [],  # External agents don't expose internal messages
        "latency_ms": latency_ms,
    }

async def run_evaluation(session: AsyncSession, endpoint_url: str | None = None) -> list[dict]:
    result_set = await session.execute(select(EvalTask))
    tasks = result_set.scalars().all()

    results = []
    for task in tasks:
        # Use external agent if endpoint_url is provided, otherwise use internal agent
        if endpoint_url:
            agent_result = await call_external_agent(endpoint_url, task.question)
            spans = []
            metrics = {"tools_called": [], "cost_usd": 0.0, "total_tokens": 0}
        else:
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
        tool_outputs = extract_tool_outputs(agent_result["messages"])
        hallucination = score_hallucination(agent_result["output"], tool_outputs)

        # Collect spans from hallucination judge call and discard
        collect_spans()
        scores = {
            "correctness": correctness["correctness"],
            "correctness_rationale": correctness["rationale"],
            "tool_use_success": tool_score["tool_use_success"],
            "missing_tools": tool_score["missing_tools"],
            "cost_usd": metrics["cost_usd"],
            "latency_ms": agent_result["latency_ms"],
            "total_tokens": metrics["total_tokens"],
            "hallucination_rate": hallucination["hallucination_rate"],
            "unsupported_claims": hallucination["unsupported_claims"],
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