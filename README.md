# Agent Builder

A platform for building and running AI agents. Design agents through a conversational chat wizard, then run them as deterministic DAG flows or autonomous ReAct loops. Supports Ollama (local), OpenAI, and Anthropic as LLM providers.

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router, TypeScript, Tailwind CSS) |
| Backend | FastAPI (Python, async) |
| LLM | Ollama · OpenAI · Anthropic (configurable via Settings) |
| Agent Runtime | LangGraph + custom ReAct engine |
| Persistence | JSON files on disk (`storage/`) |

## Quick Start

**Prerequisites:** [Ollama](https://ollama.com) running locally with at least one model pulled (if using Ollama provider).

```bash
# Pull a model (Ollama only)
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

Provider and model settings are managed through the **Settings page** (`/settings`) in the UI — no environment variables required for most setups. Settings are persisted to `storage/settings.json` and read on every LLM call.

| Setting | Default | Description |
|---|---|---|
| Provider | `ollama` | `ollama` · `openai` · `anthropic` |
| Model | `qwen3-vl:8b` | Any model name valid for the selected provider |
| Ollama base URL | `http://localhost:11434` | Ollama endpoint (Ollama provider only) |
| OpenAI API key | — | Required for OpenAI provider |
| Anthropic API key | — | Required for Anthropic provider |
| Temperature | `0.7` | Sampling temperature (0–2) |
| Max tokens | `2048` | Maximum completion tokens |

Environment variables (all optional, override defaults before first settings save):

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
│   ├── tool_library/    # 24 pre-built tools + registry (incl. 3 memory tools)
│   └── sandbox/         # Sandboxed Python executor
├── frontend/
│   └── src/
│       ├── app/         # Next.js pages (agents, runs, tool-runner)
│       ├── components/  # UI components
│       └── lib/         # API client + TypeScript types
├── storage/             # Runtime data — gitignored
│   ├── agents/          # Agent definitions
│   ├── runs/            # Run logs
│   └── memory/          # Per-agent persistent key-value stores
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
4. Watch token-level streaming output and real-time log updates via SSE
5. Usage stats (tokens, cost, latency) are shown after the run completes

## Execution Modes

**DAG Flow** — deterministic graph of nodes (`tool_call`, `llm_call`, `condition`) wired by the designer. Edges support conditional branching via Python expressions.

**ReAct Loop** — an LLM autonomously decides which tools to call each iteration (up to `max_iterations`, default 30). Activated by a `react_agent` node in the flow.

## Tools

24 pre-built tools are available across these categories:

| Category | Tools |
|---|---|
| Web & Data Fetching | `fetch_url`, `fetch_json_api`, `scrape_page_text`, `scrape_links` |
| Text & Analysis | `extract_with_regex`, `extract_emails_urls`, `text_statistics`, `keyword_search` |
| Data Transformation | `csv_parse`, `json_transform`, `merge_datasets`, `deduplicate` |
| Math & Analytics | `calculate_stats`, `compare_values` |
| Encoding & Hashing | `hash_data`, `encode_decode`, `validate_schema` |
| Date & Time | `date_calc` |
| Formatting & Output | `format_markdown_report`, `render_template` |
| PDF Processing | `extract_pdf_text` |
| Memory | `memory_read`, `memory_write`, `memory_list` |

Custom tools can be written in the builder — they run in a sandboxed Python environment with a restricted import allowlist.

Test any tool standalone via the **Tool Runner** page (`/tool-runner`).

## Persistent Agent Memory

Each agent has a persistent key-value store that survives across runs (`storage/memory/{agent_id}.json`). The three memory tools are always available in ReAct loops:

- `memory_read {key}` — retrieve a stored value
- `memory_write {key, value}` — store any JSON-serializable value
- `memory_list` — list all stored keys

Large inputs (>2000 chars) are automatically offloaded to memory before the ReAct loop starts, keeping the prompt compact. The agent's task description receives a preview and a `memory_read` instruction instead of the raw data.

## Documentation

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full system design.
