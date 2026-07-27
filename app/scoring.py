import os
import json

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()
def score_correctness(question: str, expected_answer: str, agent_output: str) -> dict:
    judge_llm = ChatGroq(
        model="llama-3.1-8b-instant",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0,
    )

    prompt = f"""You are an evaluation judge. Score how correct the agent's answer is compared to the expected answer.

Question: {question}
Expected Answer: {expected_answer}
Agent's Answer: {agent_output}

Respond with ONLY a JSON object (no markdown, no explanation):
{{"score": <float 0.0 to 1.0>, "rationale": "<one sentence>"}}"""

    response = judge_llm.invoke([
        SystemMessage(content="You are a strict evaluation judge. Respond only with valid JSON."),
        HumanMessage(content=prompt),
    ])

    try:
        result = json.loads(response.content)
        return {
            "correctness": float(result.get("score", 0.0)),
            "rationale": result.get("rationale", ""),
        }
    except (json.JSONDecodeError, ValueError):
        return {"correctness": 0.0, "rationale": "Judge failed to produce valid JSON"}
def score_tool_use(required_tools: list[str], tools_called: list[str]) -> dict:
    if not required_tools:
        return {"tool_use_success": True, "missing_tools": []}

    missing = [t for t in required_tools if t not in tools_called]
    return {
        "tool_use_success": len(missing) == 0,
        "missing_tools": missing,
    }
def score_hallucination(agent_output: str, tool_outputs: list[str]) -> dict:
    judge_llm = ChatGroq(
        model="llama-3.1-8b-instant",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0,
    )

    tool_context = "\n".join(tool_outputs) if tool_outputs else "No tool outputs available."

    prompt = f"""You are a hallucination detector. Analyze the agent's answer and determine which factual claims are NOT supported by the tool outputs provided.

Agent's Answer: {agent_output}

Tool Outputs (the only source of truth):
{tool_context}

Extract factual claims from the agent's answer. For each claim, determine if it is supported by the tool outputs.

Respond with ONLY a JSON object (no markdown):
{{"hallucination_rate": <float 0.0 to 1.0>, "unsupported_claims": ["<claim1>", "<claim2>"], "total_claims": <int>}}

Rules:
- 0.0 means all claims are supported by tool outputs
- 1.0 means no claims are supported
- General knowledge statements that don't contradict tools count as supported
- Specific numbers or facts must appear in tool outputs to be supported"""
    response = judge_llm.invoke([
        SystemMessage(content="You are a hallucination detection judge. Respond only with valid JSON."),
        HumanMessage(content=prompt),
    ])

    try:
        result = json.loads(response.content)
        return {
            "hallucination_rate": float(result.get("hallucination_rate", 0.0)),
            "unsupported_claims": result.get("unsupported_claims", []),
            "total_claims": result.get("total_claims", 0),
        }
    except (json.JSONDecodeError, ValueError):
        return {
            "hallucination_rate": 0.0,
            "unsupported_claims": [],
            "total_claims": 0,
        }