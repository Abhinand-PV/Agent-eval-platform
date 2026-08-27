# Agent Eval Platform

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/LangGraph-121212?style=for-the-badge&logo=chainlink&logoColor=white" alt="LangGraph" />
  <img src="https://img.shields.io/badge/Groq-F05032?style=for-the-badge&logo=lightning&logoColor=white" alt="Groq" />
  <img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/OpenTelemetry-000000?style=for-the-badge&logo=opentelemetry&logoColor=white" alt="OpenTelemetry" />
  <img src="https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white" alt="Vercel" />
</p>

<p align="center">
  <strong>An enterprise-grade, multi-tenant AI Agent Evaluation & Benchmarking Platform.</strong><br />
  Automatically evaluate, audit, and benchmark internal and external HTTP LLM agents across correctness, hallucination, tool usage compliance, latency, and execution cost.
</p>

<p align="center">
  <a href="https://agent-eval-platform.vercel.app"><strong>🚀 View Live Dashboard »</strong></a>
  &nbsp;&nbsp;|&nbsp;&nbsp;
  <a href="https://agent-eval-platform.vercel.app/docs"><strong>📖 Interactive API Docs (Swagger) »</strong></a>
</p>

---

## Executive Summary

Evaluating autonomous LLM agents with traditional exact-string matching or naive assertions is insufficient due to non-deterministic, open-ended outputs. 

**Agent Eval Platform** provides a robust, continuous evaluation framework designed to score AI agents against customized ground-truth datasets. It intercepts agent executions, tracks OpenTelemetry spans, runs secondary LLM judges for factual alignment and hallucination verification, and reports granular metrics in real-time.

---

## Key Features

- **Plug-and-Play Agent Integration:** Register external HTTP agent endpoints standardizing on simple JSON payloads with zero SDK lock-in.
- **LLM-as-a-Judge Scoring Engine:** Automated factual correctness scoring ($0.0$ to $1.0$) paired with secondary judge reasoning rationales.
- **Hallucination & Fact-Checking Audit:** Detects unsupported or ungrounded assertions made by agents against reference context and execution state.
- **Tool Usage Verification:** Audits whether mandatory tools (e.g., `lookup_data`, `calculate`) were correctly invoked or omitted during workflow execution.
- **Real-Time Metric Aggregation:** Tracks execution latency (ms), token volume, and estimated execution costs (USD) alongside qualitative scores.
- **OpenTelemetry Observability:** Built-in trace generation and custom span processor collection for end-to-end multi-step agent observability.
- **High-Performance Async Architecture:** Built with Python 3.11+, **FastAPI**, **SQLAlchemy 2.0 (asyncio)**, and **asyncpg**.

---

## Tech Stack & Ecosystem

| Component Layer | Technology | Purpose / Role |
|---|---|---|
| **API Framework** | [FastAPI](https://fastapi.tiangolo.com/) | Asynchronous, high-performance web framework for Python 3.11+ |
| **Agent Runtime** | [LangGraph](https://python.langchain.com/docs/langgraph/) / [LangChain](https://python.langchain.com/) | Graph-based multi-step agent flow for built-in reference agents |
| **LLM Inference Engine** | [Groq Cloud](https://groq.com/) | High-speed inference using `Llama-3.3-70b-versatile` & `Llama-3.1-8b-instant` |
| **Database & Persistence** | PostgreSQL / [SQLAlchemy 2.0 Async](https://docs.sqlalchemy.org/) | Async relational storage for tasks, agent registries, and evaluation runs |
| **Observability** | [OpenTelemetry](https://opentelemetry.io/) | Custom span processor exporting execution trace spans and token usage metrics |
| **Deployment & Hosting** | [Vercel](https://vercel.com/) / Render DB | Serverless deployment via `vercel.json` with cloud PostgreSQL storage |

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
          +-----------------------------------------+-----------------------------------------+
          |                                         |                                         |
          v                                         v                                         v
  +---------------+                         +---------------+                         +---------------+
  | POST /tasks   |                         | POST /agents  |                         | POST /evals   |
  | Define test   |                         | Register URL  |                         | Trigger Eval  |
  | benchmark     |                         | endpoint      |                         | pipeline      |
  +---------------+                         +---------------+                         +-------+-------+
                                                                                              |
                                                                                              v
                                                                                     +--------+-------+
                                                                                     |  Evaluator     |
                                                                                     +---+---------+--+
                                                                                         |         |
                                          +----------------------------------------------+         +----------------------------------------------+
                                          |                                                                                                       |
                                          v                                                                                                       v
                      +-------------------+-------------------+                                                               +-------------------+-------------------+
                      |  Internal Agent (LangGraph + Groq)    |                                                               |  External Agent Endpoint (HTTP)   |
                      |  - Tool Call Execution                |                                                               |  - Custom API / Remote Host       |
                      +-------------------+-------------------+                                                               +-------------------+-------------------+
                                          |                                                                                                       |
                                          +----------------------------------------------+---------+----------------------------------------------+
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

## Interactive API Quickstart

> [!TIP]
> You can test the live platform without setting up a local environment:
> - **Dashboard UI:** [https://agent-eval-platform.vercel.app](https://agent-eval-platform.vercel.app) — full visual interface for managing agents, test cases, and running evaluations.
> - **Swagger API Docs:** [https://agent-eval-platform.vercel.app/docs](https://agent-eval-platform.vercel.app/docs) — interactive REST API explorer.

---

### Step-by-Step Integration Workflow

#### 1. Check System Status

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

#### 2. Prepare Your External Agent Endpoint

Your agent HTTP service must accept a standard JSON payload with a `question` key and return a JSON response containing an `answer` (or `output`) key.

**Incoming HTTP Request from Platform:**
```http
POST /api/chat HTTP/1.1
Host: your-agent-service.com
Content-Type: application/json

{
  "question": "What is the capital of France and its current population?"
}
```

**Expected JSON Response:**
```json
{
  "answer": "The capital of France is Paris, and its population is approximately 67 million."
}
```

<details>
<summary>Click to view minimal Python/FastAPI External Agent example</summary>

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Query(BaseModel):
    question: str

@app.post("/ask")
async def ask(query: Query):
    # Place your LLM chain or agent execution here
    return {"answer": "Paris is the capital of France."}
```
</details>

---

#### 3. Register Your Agent Endpoint

```http
POST /agents
Content-Type: application/json

{
  "name": "Production Customer Support Agent",
  "description": "GPT-4o powered support agent endpoint",
  "endpoint_url": "https://your-agent-service.com/ask"
}
```

**Response (`200 OK`):**
```json
{
  "id": 1,
  "name": "Production Customer Support Agent",
  "description": "GPT-4o powered support agent endpoint",
  "endpoint_url": "https://your-agent-service.com/ask"
}
```

---

#### 4. Create Evaluation Tasks (Ground-Truth Dataset)

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

#### 5. Trigger Evaluation Pipeline

```http
POST /evaluations/run
Content-Type: application/json

{
  "agent_id": 1
}
```

> [!NOTE]
> If `agent_id` is omitted or set to `null`, the platform will automatically run the evaluation suite against its internal built-in **LangGraph + Groq** agent.

---

#### 6. Inspect Evaluation Metrics & Judgments

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

## Evaluation Metrics Breakdown

| Metric Key | Type / Range | Explanation & Description |
|---|---|---|
| **`correctness`** | `float` ($0.0 - 1.0$) | Evaluated by secondary LLM judge (`Llama-3.1-8b`). Measures factual semantic alignment against expected ground truth. |
| **`correctness_rationale`** | `string` | Human-readable explanation and evidence breakdown generated by the evaluation judge. |
| **`hallucination_rate`** | `float` ($0.0 - 1.0$) | Ratio of ungrounded or unsupported claims found in the agent's output relative to tool execution data ($0.0$ = fully grounded). |
| **`unsupported_claims`** | `list[str]` | Detailed list of specific sentences or assertions flagged as ungrounded by the hallucination judge. |
| **`tool_use_success`** | `boolean` | Returns `true` if the agent successfully invoked all specified `required_tools`, otherwise `false`. |
| **`missing_tools`** | `list[str]` | Identifies any mandatory tool dependencies that were omitted during agent execution. |
| **`latency_ms`** | `integer` | Total execution round-trip duration measured in milliseconds. |
| **`cost_usd`** | `float` | Estimated token financial cost in USD calculated from prompt and completion token counts. |

---

## Local Development Setup

### Prerequisites

- **Python 3.11+**
- **Docker & Docker Compose** (for PostgreSQL)
- **Groq API Key** (Free registration at [consolegroq.com](https://console.groq.com))

### Quick Start Guide

```bash
# 1. Clone the repository
git clone https://github.com/Abhinand-PV/Agent-eval-platform.git
cd Agent-eval-platform

# 2. Create & activate a virtual environment
python -m venv venv
venv\Scripts\activate          # On Windows (PowerShell/CMD)
# source venv/bin/activate     # On macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cat <<EOT > .env
DATABASE_URL=postgresql+asyncpg://postgres:Admin@localhost:5432/agent_eval
GROQ_API_KEY=your_groq_api_key_here
EOT

# 5. Start local PostgreSQL database container
docker-compose up -d

# 6. Seed initial benchmark tasks
python seed_tasks.py

# 7. Start FastAPI development server
uvicorn app.main:app --reload
```

Local Swagger Documentation will be available at: `http://localhost:8000/docs`

---

## Testing & Terminal Demonstrations

### Run Integration Test Suite
```bash
python test_eval.py
```

### Run Live Interactive Terminal Demo
To run the automated terminal demo against the live production server (with formatted table outputs):

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
│   ├── main.py             # FastAPI entry point, schemas, and endpoint definitions
│   ├── models.py           # SQLAlchemy async ORM models (EvalTask, EvalResult, AgentEndpoint)
│   ├── database.py         # Async database engine, session factory, and migration init
│   ├── agent.py            # LangGraph internal reference agent with tool bindings
│   ├── evaluator.py        # Core evaluation coordinator & HTTP agent integration worker
│   ├── scoring.py          # LLM-as-a-Judge scoring engine (correctness & hallucination)
│   ├── tools.py            # Built-in reference agent tools (lookup_data, calculate)
│   └── instrumentation.py  # OpenTelemetry tracer provider & custom span exporter
├── demo_platform.py        # Terminal demo runner with Rich table output
├── seed_tasks.py           # Benchmark database seeding script
├── test_eval.py            # Async API integration test suite
├── docker-compose.yml      # Local PostgreSQL container service configuration
├── Dockerfile              # Container image build configuration
├── requirements.txt        # Python package dependencies
├── vercel.json             # Vercel serverless deployment manifest
└── README.md               # Project documentation
```

---

## Deployment Configuration

The platform is designed for seamless deployment on serverless infrastructure.

### Deploying to Vercel

1. **Fork** this repository to your GitHub account.
2. Connect the repository to your [Vercel Workspace](https://vercel.com).
3. Configure the following **Environment Variables** in Vercel Project Settings:
   - `DATABASE_URL`: Your cloud PostgreSQL connection URI (e.g., Supabase, Render, ElephantSQL using `postgresql+asyncpg://` or `postgresql://`).
   - `GROQ_API_KEY`: Your Groq API authentication key.
4. Trigger Deployment! Vercel handles serverless routing via `vercel.json`.

---

## License

Distributed under the **MIT License**. See `LICENSE` for more information.
