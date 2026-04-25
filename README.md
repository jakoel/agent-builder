# Agent Builder

A platform for building and running AI agents powered by local Ollama models. Design agents through a conversational chat wizard, then run them as deterministic DAG flows or autonomous ReAct loops.

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router, TypeScript, Tailwind CSS) |
| Backend | FastAPI (Python, async) |
| LLM | Ollama (local, `localhost:11434`) |
| Agent Runtime | LangGraph + custom ReAct engine |
| Persistence | JSON files on disk (`storage/`) |

## Quick Start

**Prerequisites:** [Ollama](https://ollama.com) running locally with at least one model pulled.

```bash
# Pull a model
ollama pull qwen3-vl:8b

# Run setup (installs backend deps, frontend deps)
./setup.sh

# Terminal 1 — backend
cd backend && uvicorn main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend && npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Configuration

Environment variables (all optional):

| Variable | Default | Description |
|---|---|---|
| `AB_OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama endpoint |
| `AB_DEFAULT_MODEL` | `qwen3-vl:8b` | Model used for building and running |
| `AB_STORAGE_PATH` | `./storage` | Where agents and runs are persisted |

## Project Structure

```
agent_builder/
├── backend/
│   ├── engine/          # ReAct loop + LangGraph DAG builder
│   ├── routers/         # FastAPI route handlers
│   ├── schemas/         # Pydantic data models
│   ├── services/        # Business logic (builder, runner, agents)
│   ├── tool_library/    # 21 pre-built tools + registry
│   └── sandbox/         # Sandboxed Python executor
├── frontend/
│   └── src/
│       ├── app/         # Next.js pages (agents, runs, tool-runner)
│       ├── components/  # UI components
│       └── lib/         # API client + TypeScript types
├── storage/             # Runtime data — gitignored
├── ARCHITECTURE.md      # Full system design
└── setup.sh
```

## Building an Agent

1. Click **New Agent** in the sidebar
2. Describe what you want the agent to do — the wizard generates system prompts, tools, and a flow definition
3. Review and edit the generated artifacts in the chat
4. Click **Finalize** to publish the agent

## Running an Agent

1. Open an agent's detail page
2. Go to the **Run** tab
3. Provide input as JSON and click **Run Agent**
4. Watch real-time log output streamed via SSE

## Execution Modes

**DAG Flow** — deterministic graph of nodes (`tool_call`, `llm_call`, `condition`) wired by the designer. Edges support conditional branching via Python expressions.

**ReAct Loop** — an LLM autonomously decides which tools to call each iteration (up to `max_iterations`, default 30). Activated by a `react_agent` node in the flow.

## Tools

21 pre-built tools are available (web scraping, JSON transforms, text processing, and more). You can also write custom tools in the builder — they run in a sandboxed Python environment with a restricted import allowlist.

Test any tool standalone via the **Tool Runner** page (`/tool-runner`).

## Documentation

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full system design.
