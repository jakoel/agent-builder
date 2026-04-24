# Agent Builder — Claude Code Guide

## Project

A platform for building and running AI agents powered by local Ollama models. Users design agents via a chat wizard; agents run as deterministic DAG flows or autonomous ReAct loops.

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full system design — read it before making any non-trivial changes.

## Stack

- **Backend**: FastAPI + Python (`backend/`)
- **Frontend**: Next.js 14 App Router + TypeScript (`frontend/src/`)
- **LLM**: Ollama only (no cloud APIs)
- **Persistence**: JSON files on disk (`storage/`)

## Running Locally

```bash
# Terminal 1 — backend
cd backend && uvicorn main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend && npm run dev
```

Requires Ollama running at `localhost:11434`. Default model: `llama3.2:latest`.

## Key Files to Know

| What | Where |
|---|---|
| All agent + flow schemas | `backend/schemas/agent.py` |
| ReAct loop + prompt + parser | `backend/engine/react_engine.py` |
| Agent run execution | `backend/services/runner_service.py` |
| LangGraph DAG builder | `backend/engine/graph_builder.py` |
| Tool registry (21 tools, with schemas) | `backend/tool_library/registry.py` |
| Sandbox executor | `backend/sandbox/executor.py` |
| Builder wizard logic | `backend/services/builder_service.py` |
| All API calls from frontend | `frontend/src/lib/api.ts` |
| Frontend types | `frontend/src/lib/types.ts` |

## Coding Rules

- Tools must accept `input_data: dict` and return `dict`
- Allowed sandbox imports: `json re datetime math requests bs4 urllib collections itertools functools hashlib base64 html csv time random string typing pypdf`
- Blocked: `os sys subprocess socket importlib ctypes pickle sqlite3 pathlib`
- Every new pre-built tool in `tool_library/` must have a matching entry in `registry.py` with both `parameters` and `output_schema` JSON Schemas
- `_save_run()` must be called after every meaningful step in any run loop so the frontend gets live log updates
- Do not merge all `tool_results` into a tool's `input_data` — pass only `{**input_data, **tool_args}`

## Flow Node Types

`start` | `end` | `tool_call` | `llm_call` | `condition` | `react_agent`

`react_agent` runs the ReAct loop (max `max_iterations`, default 30). The loop is in `runner_service._react_run()` and mirrored in `graph_builder.py`.

## Adding a Pre-built Tool

1. Create `backend/tool_library/{tool_name}.py` — single function, `input_data: dict → dict`
2. Add entry to `TOOL_CATALOG` in `backend/tool_library/registry.py` with `parameters` and `output_schema`
3. Test it via the Tool Runner page (`/tool-runner`) before wiring into agents

## Type Checking

```bash
cd frontend && npx tsc --noEmit
```

Pre-existing errors in `StepDesign.tsx` (lines 214, 239, 305, 369) — ignore these, they are known and unrelated to new work.
