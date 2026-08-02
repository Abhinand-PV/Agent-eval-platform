# Agent Eval Platform

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/LangGraph-121212?style=for-the-badge&logo=chainlink" alt="LangGraph" />
  <img src="https://img.shields.io/badge/Groq-F05032?style=for-the-badge&logo=lightning" alt="Groq" />
  <img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white" alt="Vercel" />
  <img src="https://img.shields.io/badge/OpenTelemetry-000000?style=for-the-badge&logo=opentelemetry" alt="OpenTelemetry" />
</p>

A production-ready, multi-tenant AI agent evaluation platform that automatically tests, benchmarks, and scores any AI agent (internal or external HTTP endpoints) against custom datasets — measuring correctness, hallucination rate, tool usage compliance, latency, and token cost.

**Live API & Interactive Docs:** [https://agent-eval-platform.vercel.app/docs](https://agent-eval-platform.vercel.app/docs)

---

## Overview

Evaluating LLM agents is challenging because exact string matching fails on open-ended outputs. **Agent Eval Platform** provides an end-to-end automated pipeline for continuous AI evaluation:

1. **Benchmarking & Datasets:** Define ground-truth test datasets (`tasks`) containing target questions, expected ground-truth answers, and mandatory tools that should be invoked.
2. **Flexible Agent Integration:** Register custom external HTTP agent endpoints or evaluate against the platform's internal **LangGraph** multi-tool agent powered by **Groq Llama 3.3 70B**.
3. **LLM-as-Judge Scoring:** Uses secondary LLM judges (powered by **Groq Llama 3.1 8B**) to evaluate factual correctness and detect unsupported claims (hallucination rate) with natural language reasoning.
4. **Tool Call & Metric Auditing:** Intercepts agent tool executions and OpenTelemetry telemetry spans to measure tool compliance, request latency, and estimated token execution costs.

---

## Key Features

- **Plug-and-Play External Agent Support:** Register any external HTTP agent standardizing on JSON payload exchange. No SDK integration required.
- **LLM-as-Judge Evaluation:** Automatic scoring of correctness (0.0 to 1.0) and hallucination rate (0.0 to 1.0) complete with clear natural language rationales.
- **Tool Usage Verification:** Validates whether required tools (e.g., `lookup_data`, `calculate`) were invoked during execution and identifies missing tool calls.
- **Comprehensive Metric Reports:** Real-time feedback covering correctness score, hallucination breakdown, missing tools, response latency (ms), and cost estimations (USD).
- **OpenTelemetry Observability:** Distributed trace generation and custom span collection to track internal execution graphs and token counts.
- **High-Performance Async Pipeline:** Fully asynchronous core leveraging **FastAPI**, **SQLAlchemy 2.0 (asyncio)**, and **asyncpg**.

---

## Tech Stack

| Layer | Technology | Description |
|---|---|---|
| **API Framework** | FastAPI | High-performance, asynchronous web framework for Python 3.11+ |
| **Agent Framework** | LangGraph + LangChain | Graph-based LLM workflow execution for internal agents |
| **LLM Provider** | Groq Cloud | Llama 3.3 70B (Internal Agent) & Llama 3.1 8B (LLM Judge) |
| **Database** | PostgreSQL | Persistent state storage hosted on Render |
| **ORM** | SQLAlchemy (Async) | Modern async database operations with PostgreSQL |
| **Deployment** | Vercel | Serverless hosting configuration via `vercel.json` |
| **Observability** | OpenTelemetry | Custom span processor and tracer provider setup |

---

## System Architecture

```
                                 +-----------------------------------+
                                 |       User / Client / CI          |
                                 +-----------------+-----------------+
                                                   |
                                                   v
                                     +-------------+-------------+
                                     |  FastAPI App (Vercel)     |
                                     +-------------+-------------+
                                                   |
          +----------------------------------------+----------------------------------------+
          |                                        |                                        |
          v                                        v                                        v
  +---------------+                        +---------------+                        +---------------+
  | POST /tasks   |                        | POST /agents  |                        | POST /evals   |
  | Define test   |                        | Register URL  |                        | Trigger Eval  |
  | benchmark     |                        | endpoint      |                        | pipeline      |
  +---------------+                        +---------------+                        +-------+-------+
                                                                                            |
                                                                                            v
                                                                                   +--------+-------+
                                                                                   |  Evaluator     |
                                                                                   +---+---------+--+
                                                                                       |         |
                                         +---------------------------------------------+         +---------------------------------------------+
                                         |                                                                                                     |
                                         v                                                                                                     v
                     +-------------------+-------------------+                                                             +-------------------+-------------------+
                     |  Internal Agent (LangGraph + Groq)    |                                                             |  External Agent Endpoint (HTTP)   |
                     |  - Tool Call Execution                |                                                             |  - Custom API / Remote Host       |
                     +-------------------+-------------------+                                                             +-------------------+-------------------+
                                         |                                                                                                     |
                                         +---------------------------------------------+---------+---------------------------------------------+
                                                                                       |
                                                                                       v
                                                                           +-----------+-----------+
                                                                           |  LLM-as-Judge Scorer  |
                                                                           |  - Correctness Judge  |
                                                                           |  - Hallucination Judge|
                                                                           +-----------+-----------+
                                                                                       |
                                                                                       v
                                                                           +-----------+-----------+
                                                                           |  PostgreSQL Database  |
                                                                           |  (Tasks, Evals, Spans)|
                                                                           +-----------------------+
```

---

## Quickstart: Using the Live Platform

No local installation is required to test the platform. Access the live Swagger documentation to interact with the API endpoints:

**[https://agent-eval-platform.vercel.app/docs](https://agent-eval-platform.vercel.app/docs)**

---

### Step-by-Step Integration Guide

#### Step 1 — Check Platform Health

```http
GET /health
```
**Response:**
```json
{
  "status": "ok"
}
```

---

#### Step 2 — Prepare Your External Agent Endpoint

Your agent must accept an HTTP `POST` request with a JSON body containing a `question` key and respond with JSON containing an `answer` (or `output`) key.

**Sample Request sent by Platform:**
```json
POST https://your-agent-service.com/api/chat
Content-Type: application/json

{
  "question": "What is the capital of France and its current population?"
}
```

**Expected Response from Your Agent:**
```json
{
  "answer": "The capital of France is Paris, and its population is approximately 67 million."
}
```

*Example minimal Python/FastAPI agent:*
```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Query(BaseModel):
    question: str

@app.post("/ask")
async def ask(query: Query):
    # Your custom LLM / Agent logic here
    return {"answer": "Paris is the capital of France."}
```

---

#### Step 3 — Register Your Agent

```http
POST /agents
Content-Type: application/json

{
  "name": "Production Customer Support Agent",
  "description": "GPT-4o powered support bot",
  "endpoint_url": "https://your-agent-service.com/ask"
}
```

**Response:**
```json
{
  "id": 1,
  "name": "Production Customer Support Agent",
  "description": "GPT-4o powered support bot",
  "endpoint_url": "https://your-agent-service.com/ask"
}
```

---

#### Step 4 — Create Evaluation Benchmark Tasks

```http
POST /tasks
Content-Type: application/json

{
  "question": "What is the capital of Japan and what is 15 multiplied by 8?",
  "expected_answer": "The capital of Japan is Tokyo, and 15 multiplied by 8 is 120.",
  "required_tools": ["lookup_data", "calculate"]
}
```

---

#### Step 5 — Trigger Automated Evaluation

```http
POST /evaluations/run
Content-Type: application/json

{
  "agent_id": 1
}
```
> *Note: If `agent_id` is omitted or `null`, the platform automatically evaluates against its built-in internal agent.*

---

#### Step 6 — Review Comprehensive Evaluation Results

```json
{
  "status": "completed",
  "results": [
    {
      "task_id": 1,
      "question": "What is the capital of Japan and what is 15 multiplied by 8?",
      "agent_output": "The capital of Japan is Tokyo. 15 * 8 equals 120.",
      "scores": {
        "correctness": 0.98,
        "correctness_rationale": "The answer accurately states both the capital of Japan and the correct mathematical product.",
        "tool_use_success": true,
        "missing_tools": [],
        "hallucination_rate": 0.0,
        "unsupported_claims": [],
        "cost_usd": 0.00024,
        "latency_ms": 1150,
        "total_tokens": 312
      }
    }
  ]
}
```

---

## Evaluation Metrics Explained

| Metric | Range / Type | Explanation |
|---|---|---|
| **`correctness`** | `0.0` – `1.0` | Evaluated by Llama 3.1 8B judge. Measures how accurately the agent output matches the expected ground-truth statement. |
| **`correctness_rationale`** | `string` | Human-readable explanation provided by the judge justifying the score. |
| **`hallucination_rate`** | `0.0` – `1.0` | Proportion of factual claims in the agent output not backed by tool execution context or verified sources (`0.0` = zero hallucination). |
| **`unsupported_claims`** | `list[str]` | List of specific statements or numbers flagged as ungrounded by the hallucination detector. |
| **`tool_use_success`** | `boolean` | `true` if the agent called all specified `required_tools`, otherwise `false`. |
| **`missing_tools`** | `list[str]` | Identifies which required tools were omitted during the execution. |
| **`latency_ms`** | `integer` | Total round-trip execution latency in milliseconds. |
| **`cost_usd`** | `float` | Estimated token cost calculation based on prompt and completion token counts. |

---

## Local Development Setup

### Prerequisites

- **Python 3.11+**
- **Docker & Docker Compose**
- **Groq API Key** (Get a free key at [console.groq.com](https://console.groq.com))

### Quick Setup

```bash
# 1. Clone the repository
git clone https://github.com/Abhinand-PV/Agent-eval-platform.git
cd Agent-eval-platform

# 2. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # On Windows (PowerShell/CMD)
# source venv/bin/activate     # On macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create environment file (.env)
cat <<EOT > .env
DATABASE_URL=postgresql+asyncpg://postgres:Admin@localhost:5432/agent_eval
GROQ_API_KEY=your_groq_api_key_here
EOT

# 5. Spin up PostgreSQL database container
docker-compose up -d

# 6. Seed sample benchmark tasks
python seed_tasks.py

# 7. Run development server
uvicorn app.main:app --reload
```

Access local API documentation at: `http://localhost:8000/docs`

---

## Terminal Demo & Test Scripts

Run the included automated test suite locally:

```bash
python test_eval.py
```

Run an end-to-end evaluation terminal demonstration against the live production server:

```bash
pip install requests rich
python demo_platform.py https://agent-eval-platform.vercel.app
```

---

## Repository Structure

```
agent-eval-platform/
├── app/
│   ├── __init__.py
│   ├── main.py             # FastAPI routes, schemas, and app initialization
│   ├── models.py           # SQLAlchemy async database models (EvalTask, EvalResult, AgentEndpoint)
│   ├── database.py         # Async engine setup, session maker, and DB init
│   ├── agent.py            # LangGraph internal agent flow with tool binding
│   ├── evaluator.py        # Evaluation workflow manager & HTTP agent caller
│   ├── scoring.py          # LLM-as-judge scoring logic (correctness & hallucination)
│   ├── tools.py            # Agent tools (lookup_data, calculate)
│   └── instrumentation.py  # OpenTelemetry tracing setup & span metrics exporter
├── demo_platform.py        # Terminal demo script with rich table output
├── seed_tasks.py           # Seeding script for sample benchmark tasks
├── test_eval.py            # Integration test runner using FastAPI TestClient
├── docker-compose.yml      # Local PostgreSQL service definition
├── Dockerfile              # Container definition for containerized deployment
├── requirements.txt        # Python package dependencies
├── vercel.json             # Vercel Serverless deployment config
└── README.md
```

---

## Deployment

The live production instance is deployed on **Vercel** with a serverless PostgreSQL database hosted on **Render**.

### Deploying Your Own Instance:

1. **Fork** this repository.
2. Connect your fork to [Vercel](https://vercel.com).
3. Set the following **Environment Variables** in Vercel settings:
   - `DATABASE_URL`: Your PostgreSQL connection string (PostgreSQL serverless URL using `postgresql+asyncpg://` or `postgresql://`).
   - `GROQ_API_KEY`: Your Groq API key.
4. Deploy! Vercel automatically deploys commits to `main`.

---

## License

This project is open-source under the [MIT License](LICENSE).

