# Agent Eval Platform

A production-ready, multi-tenant AI agent evaluation platform that automatically tests and scores any AI agent against custom benchmarks — measuring correctness, hallucination rate, tool usage, latency, and cost.

**Live API:** [https://agent-eval-platform.vercel.app/docs](https://agent-eval-platform.vercel.app/docs)

---

## Overview

Agent Eval Platform provides a structured pipeline for evaluating the quality of AI agents. Users can define evaluation tasks with expected answers, register their own agent endpoints, and trigger automated scoring across all tasks. Results are stored in a persistent database and returned as a detailed JSON report.

The platform uses a secondary LLM (LLM-as-Judge) to assess correctness and hallucination rather than relying on exact string matching, making it suitable for evaluating open-ended language model outputs.

---

## Features

- **External Agent Support** — Register any HTTP-based agent endpoint and evaluate it without modifying the platform
- **LLM-as-Judge Scoring** — A secondary LLM scores correctness and hallucination with natural language rationale
- **Tool Use Verification** — Tracks whether the agent called the required tools for each task
- **Multi-Metric Reports** — Correctness, hallucination rate, tool use success, latency, and estimated token cost per task
- **Interactive API Docs** — Fully usable from the browser via Swagger UI, no client code required
- **Async Architecture** — Built with FastAPI and asyncpg for non-blocking database operations
- **OpenTelemetry Instrumentation** — Distributed tracing included for observability

---

## Tech Stack

| Layer | Technology |
|---|---|
| API Framework | FastAPI |
| Agent Framework | LangGraph + LangChain |
| LLM Provider | Groq (Llama 3.3 70B for agent, Llama 3.1 8B for judge) |
| Database | PostgreSQL (hosted on Render) |
| ORM | SQLAlchemy (async) |
| Deployment | Vercel (Serverless Functions) |
| Observability | OpenTelemetry |

---

## Architecture

```
User / External Agent
        |
        v
  FastAPI (Vercel)
  +-----------------------------+
  |  POST /tasks                |  <- Define evaluation tasks
  |  POST /agents               |  <- Register your agent endpoint
  |  POST /evaluations/run      |  <- Trigger evaluation pipeline
  +-------------+---------------+
                |
       +--------v--------+
       |   Evaluator     |
       |  +-----------+  |
       |  |  Agent    |  |  <- Calls your endpoint OR internal agent
       |  +-----+-----+  |
       |  +-----v-----+  |
       |  |  Scorer   |  |  <- LLM-as-Judge (correctness + hallucination)
       |  +-----+-----+  |
       +--------+---------+
                |
       +--------v--------+
       |   PostgreSQL    |  <- Stores tasks, agents, and results
       |   (Render)      |
       +-----------------+
```

---

## Using the Live Platform

No installation is required. Navigate to the Swagger UI and interact with all endpoints directly in your browser.

**[https://agent-eval-platform.vercel.app/docs](https://agent-eval-platform.vercel.app/docs)**

---

### Step 1 — Verify the API is Running

**`GET /health`**

Returns `{ "status": "ok" }` if the API is reachable. Use this as a quick sanity check before running evaluations.

---

### Step 2 — Prepare Your Agent Endpoint

Your agent must expose a single HTTP `POST` endpoint that accepts a `question` field and returns an `answer` field.

**Request the platform sends to your agent:**
```json
POST https://your-agent.example.com/ask

{
  "question": "What is the capital of India?"
}
```

**Expected response from your agent:**
```json
{
  "answer": "The capital of India is New Delhi."
}
```

> The platform also accepts `"output"` as an alternative response key.

**Minimal example (Python / Flask):**

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.post("/ask")
def ask():
    question = request.json.get("question")
    answer = your_llm_call(question)
    return jsonify({"answer": answer})
```

Deploy this to any publicly accessible host (Render, Railway, Fly.io, etc.) before proceeding.

---

### Step 3 — Register Your Agent

**`POST /agents`**

```json
{
  "name": "My GPT-4 Agent",
  "description": "A customer support agent powered by GPT-4o",
  "endpoint_url": "https://your-agent.example.com/ask"
}
```

**Response:**
```json
{
  "id": 1,
  "name": "My GPT-4 Agent",
  "description": "A customer support agent powered by GPT-4o",
  "endpoint_url": "https://your-agent.example.com/ask"
}
```

Save the returned `id`. You will need it when triggering the evaluation.

---

### Step 4 — Create Evaluation Tasks

**`POST /tasks`**

Define the questions and expected answers to test your agent against. Repeat this step for each task you want to include.

```json
{
  "question": "What is the capital of India?",
  "expected_answer": "The capital of India is New Delhi.",
  "required_tools": ["lookup_data"]
}
```

| Field | Type | Description |
|---|---|---|
| `question` | string | The prompt sent to your agent |
| `expected_answer` | string | The ground-truth answer used for scoring |
| `required_tools` | list | Tools the agent must call: `"lookup_data"`, `"calculate"`, or `[]` |

---

### Step 5 — Run the Evaluation

**`POST /evaluations/run`**

```json
{
  "agent_id": 1
}
```

Omit `agent_id` or set it to `null` to evaluate using the platform's built-in internal agent (Llama 3.3 70B).

The platform will iterate over all saved tasks, call your agent endpoint for each question, score every response using the LLM judge, and return a full results report.

**Response:**
```json
{
  "status": "completed",
  "results": [
    {
      "task_id": 1,
      "question": "What is the capital of India?",
      "agent_output": "The capital of India is New Delhi.",
      "scores": {
        "correctness": 0.98,
        "correctness_rationale": "The answer exactly matches the expected answer.",
        "tool_use_success": true,
        "missing_tools": [],
        "hallucination_rate": 0.0,
        "unsupported_claims": [],
        "cost_usd": 0.0003,
        "latency_ms": 1240,
        "total_tokens": 278
      }
    }
  ]
}
```

---

### Step 6 — Interpret the Scores

| Metric | Range | Description |
|---|---|---|
| `correctness` | 0.0 – 1.0 | Semantic similarity between agent output and expected answer |
| `tool_use_success` | true / false | Whether all required tools were invoked |
| `missing_tools` | list | Names of any required tools that were not called |
| `hallucination_rate` | 0.0 – 1.0 | Fraction of claims not grounded in tool outputs |
| `unsupported_claims` | list | Specific claims the judge identified as unsupported |
| `latency_ms` | integer | Agent response time in milliseconds |
| `cost_usd` | float | Estimated LLM cost for this task |

---

### Step 7 — View All Registered Agents

**`GET /agents`**

Returns a list of all agents registered on the platform, including their IDs and endpoint URLs.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Check API status |
| POST | `/tasks` | Create a new evaluation task |
| POST | `/agents` | Register an external agent endpoint |
| GET | `/agents` | List all registered agents |
| POST | `/evaluations/run` | Run evaluation against all tasks |

Full interactive documentation: [https://agent-eval-platform.vercel.app/docs](https://agent-eval-platform.vercel.app/docs)

---

## Running Locally

### Prerequisites

- Python 3.11+
- Docker Desktop
- Groq API key ([get one free at console.groq.com](https://console.groq.com))

### Setup

```bash
# Clone the repository
git clone https://github.com/Abhinand-PV/Agent-eval-platform.git
cd Agent-eval-platform

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
# Create a .env file with the following:
# DATABASE_URL=postgresql://postgres:Admin@localhost:5432/agent_eval
# GROQ_API_KEY=your_groq_api_key_here

# Start the PostgreSQL database
docker-compose up -d

# Seed sample evaluation tasks (optional)
python seed_tasks.py

# Start the development server
uvicorn app.main:app --reload
```

Open [http://localhost:8000/docs](http://localhost:8000/docs) to access the local Swagger UI.

---

## Terminal Demo Script

Run an end-to-end demo against the production API from your terminal:

```bash
pip install requests rich
python demo_platform.py https://agent-eval-platform.vercel.app
```

The script will check the API health, create a sample evaluation task, trigger the evaluation pipeline, and display the results in a formatted table.

---

## Project Structure

```
agent-eval-platform/
├── app/
│   ├── main.py             # FastAPI routes and request models
│   ├── models.py           # SQLAlchemy database models
│   ├── database.py         # Async database engine and session setup
│   ├── agent.py            # Internal LangGraph agent
│   ├── evaluator.py        # Evaluation pipeline and external agent caller
│   ├── scoring.py          # LLM-as-judge scoring functions
│   ├── tools.py            # Agent tools (lookup_data, calculate)
│   └── instrumentation.py  # OpenTelemetry setup
├── demo_platform.py        # Terminal demo script
├── seed_tasks.py           # Script to seed sample tasks
├── docker-compose.yml      # Local PostgreSQL configuration
├── requirements.txt
└── vercel.json             # Vercel serverless configuration
```

---

## Deployment

The platform is deployed on **Vercel** with a **Render** PostgreSQL database.

To deploy your own instance:

1. Fork this repository
2. Connect it to a new Vercel project
3. Add the following environment variables in Vercel project settings:
   - `DATABASE_URL` — PostgreSQL connection string (Render, Supabase, or Neon)
   - `GROQ_API_KEY` — Your Groq API key

Vercel will automatically deploy on every push to the `main` branch.

---

## License

MIT License — free to use, fork, and extend.
