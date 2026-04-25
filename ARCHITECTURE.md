# Architecture

## Overview

Agent Builder is a platform for creating and running AI agents. Users design agents through a chat wizard, then run them against tasks. The platform supports two execution models: a deterministic DAG flow (nodes wired by the designer) and a dynamic ReAct loop (the LLM decides which tools to call at runtime). LLM calls are routed through a unified `LLMService` that supports Ollama, OpenAI, and Anthropic — switchable at runtime via the Settings page.

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router, TypeScript, Tailwind CSS) |
| Backend | FastAPI (Python, async) |
| LLM | Ollama · OpenAI · Anthropic (via `LLMService`) |
| Agent Runtime | LangGraph + custom ReAct engine |
| Persistence | JSON files on disk (`storage/agents/`, `storage/runs/`, `storage/settings.json`) |
| Tool Sandbox | Python subprocess with import blocklist |

Environment variables (prefix `AB_`):
- `AB_OLLAMA_BASE_URL` — default `http://localhost:11434`
- `AB_STORAGE_PATH` — default `./storage`
- `AB_DEFAULT_MODEL` — default `qwen3-vl:8b`

Runtime configuration is managed via `storage/settings.json` (provider, API keys, temperature, max_tokens). Settings are read fresh on every LLM call so changes take effect immediately without a restart.

---

## Backend

### Entry point
`backend/main.py` — FastAPI app, CORS middleware, router registration, storage dir creation on startup.

### Routers (`backend/routers/`)

| File | Prefix | Responsibility |
|---|---|---|
| `agents.py` | `/api/agents` | CRUD for agent definitions; `POST /` accepts a full `AgentDefinition` for programmatic creation |
| `builder.py` | `/api/builder` | Conversational agent-building wizard |
| `runs.py` | `/api/runs` | Start, poll, cancel agent runs; SSE log + token streaming |
| `tool_library.py` | `/api/tool-library` | List pre-built tools, get detail, run a tool directly |
| `models.py` | `/api/models` | List available Ollama models |
| `settings.py` | `/api/settings` | Read/write `storage/settings.json` (provider, API keys, temperature, max_tokens) |

### Schemas (`backend/schemas/`)

**`agent.py`** — core data model:
- `ToolDefinition` — name, description, `parameters` (JSON Schema), `output_schema` (JSON Schema), `code`, `filename`
- `FlowNode` — id, label, `type` (`start | end | tool_call | llm_call | condition | react_agent`), `tool_name`, `prompt_template`, `max_iterations` (default 30, used by `react_agent`)
- `FlowEdge` — source, target, optional `condition` (Python expression evaluated against `tool_results`)
- `FlowDefinition` — nodes, edges, `entry_node`
- `AgentDefinition` — full agent: id, name, description, system_prompt, model, tools, flow, status

**`run.py`** — `RunResult`, `RunLog` (with `level`), `RunRequest`, `TokenUsage`

`TokenUsage` accumulates per-run: `prompt_tokens`, `completion_tokens`, `total_tokens`, `cost_usd`. `RunResult` carries `usage: TokenUsage`, `llm_calls: int`, `total_llm_latency_ms: float`, and `provider: str`.

**`builder.py`** — `BuilderMessage`, `BuilderSession`, `ToolValidationResult`, `ValidateToolsResponse`, `EnhanceToolResponse`

### Services (`backend/services/`)

**`LLMService`** — unified async LLM client. Reads provider config from `settings_service.load()` on every call. Methods:
- `chat(**kwargs) -> ChatResult` — single-turn non-streaming call
- `chat_stream(**kwargs) -> AsyncGenerator[(chunk, Optional[ChatResult])]` — yields text chunks; final item carries the completed `ChatResult` with token counts, cost, and latency

`ChatResult` dataclass: `content: str`, `prompt_tokens: int`, `completion_tokens: int`, `cost_usd: float`, `latency_ms: float`.

Provider routing:
- **Ollama** — httpx, passes `temperature` + `num_predict` in `options`; token counts from `prompt_eval_count` / `eval_count`
- **OpenAI** — httpx REST with `stream_options: {include_usage: true}` so streaming calls still return token counts
- **Anthropic** — `anthropic.AsyncAnthropic` SDK with `.messages.stream()`; client instance cached by `(api_key, base_url)` pair

**`llm_pricing.py`** — `PRICING` dict of `{provider: {model: (input_per_M, output_per_M)}}`. `compute_cost(provider, model, prompt_tokens, completion_tokens) -> float` with prefix-match fallback for versioned model names (e.g. `claude-sonnet-4-6-20250101`).

**`settings_service.py`** — shared reader/writer for `storage/settings.json`. `load() -> dict`, `save(data) -> None`, `DEFAULTS` dict. Read fresh on every LLM call so UI changes take effect immediately.

**`AgentService`** — file-based CRUD for `AgentDefinition`. Agents stored as JSON in `storage/agents/{id}.json`. `create_full_agent(AgentDefinition)` accepts a complete definition (used by `POST /api/agents`) and auto-assigns an id if omitted — this is the entry point for programmatic agent creation, bypassing the builder wizard entirely.

**`BuilderService`** — orchestrates the wizard flow. Uses `LLMService` internally. Phase handlers:
- `refine_prompt` — takes user description, returns polished system prompt
- `suggest_tools` — returns JSON tool list, preferring pre-built tools over custom
- `generate_tool_code` — LLM-generates Python code, self-validates with a second LLM pass + `compile()`
- `generate_flow` — auto-builds a linear DAG from the agent's tool list
- `finalize` — validates agent completeness, sets status to `ready`
- `validate_tools` — runs each tool through the sandbox with stub inputs
- `enhance_tool` — LLM rewrites a tool per user instruction

**`RunnerService`** — manages run lifecycle. Runs execute as `asyncio.Task`. Key methods:
- `_execute_run()` — walks the flow DAG node by node; `react_agent` nodes delegate to `_react_run()`
- `_react_run()` — the ReAct loop; auto-offloads large inputs and injects memory tools before starting
- `_stream_chat()` — calls `llm.chat_stream()`, writes chunks to `_live_streams[run_id]`, aggregates `ChatResult` into `run.usage`
- `_call_tool(tool_name, code, input_data, agent_id)` — central dispatch: checks `NATIVE_TOOLS` first, falls back to sandbox
- `_offload_large_inputs(input_data, agent_id)` — moves string values >2000 chars to agent memory, replaces them with a compact preview + `memory_read` instruction
- `get_live_output(run_id) -> str` — returns current token buffer for SSE polling

`_live_streams: dict[str, str]` — in-memory buffer holding the current partial LLM response per run. Cleared when the run completes.

**`SandboxService`** — thin wrapper over `sandbox/executor.py`.

### Sandbox (`backend/sandbox/`)

**`executor.py`** — `execute(code, input_data, timeout)`:
1. Wraps tool code in a Python script with restriction header prepended
2. Serialises `input_data` as JSON, deserialises inside the subprocess
3. Runs in a temp file via `subprocess.run`
4. Captures stdout, parses as JSON, returns as dict
5. Raises `RuntimeError` on non-zero exit, timeout, or invalid JSON output

**`restrictions.py`** — generates the restriction header prepended to every tool execution:
- Import blocker (meta-path hook) blocking: `os`, `sys`, `subprocess`, `shutil`, `socket`, `importlib`, `ctypes`, `signal`, `multiprocessing`, `threading`, `pickle`, `sqlite3`, `pathlib`, etc.
- Builtin removal: `open`, `input`, `exit`, `quit`, `breakpoint`
- Pre-imports `requests`, `urllib3`, `logging` before the blocker installs (they pull in threads as side effects)

### Engine (`backend/engine/`)

**`state.py`** — `AgentState` TypedDict: `input_data`, `current_node`, `messages`, `tool_results`, `output_data`, `error`

**`tool_loader.py`** — wraps each `ToolDefinition` as an async callable via `SandboxService`

**`graph_builder.py`** — compiles an `AgentDefinition` into a LangGraph `StateGraph`. Each node type becomes a LangGraph node function. Includes `react_agent` node type (see ReAct Engine below).

**`react_engine.py`** — the ReAct (Reasoning + Acting) loop implementation:

- `format_tool_schemas(tools)` — renders tool list as a structured text block the LLM reads before acting. For each tool: name, description, parameters with `(required)` markers and defaults, and return field descriptions from `output_schema`. This is the **tool schema contract**.
- `parse_react_response(text)` — extracts `("ACTION", (tool_name, args))` or `("FINAL", answer)` from LLM output. Uses **brace-counting** (not regex) for JSON extraction so nested objects parse correctly.
- `build_scratchpad(entries)` — **tiered context management**:
  - **Full tier** (most recent 2 iterations): raw Thought + Action + Input + Observation (char-capped at 1,500). Raw so the model can use the data as tool input.
  - **Summary tier** (next 6 iterations): one-line summary — `Step N: tool_name → key=val, count=5`. Key scalars only, lists reduced to item count.
  - **Dropped** (older than 8 iterations): excluded entirely.
  - **Character budget**: hard cap of 6,000 chars applied newest-first as a final safety net.
- `REACT_SYSTEM` — system prompt enforcing strict `Thought / Action / Input` or `Final Answer` format.

### Tool Library (`backend/tool_library/`)

24 pre-built tools. Each is a standalone Python file with a single function named after the tool, accepting `input_data: dict` and returning `dict`.

**`registry.py`** — `TOOL_CATALOG`: list of dicts with `name`, `display_name`, `description`, `category`, `filename`, `parameters` (JSON Schema), `output_schema` (JSON Schema). Also exports `NATIVE_TOOLS: dict[str, Callable]` — tools that run outside the sandbox, called directly with `(input_data, storage_path, agent_id)`. Functions: `get_catalog()`, `get_tool_code(name)`, `get_tool_detail(name)`.

Categories and tools:
- **Web & Data Fetching**: `fetch_url`, `fetch_json_api`, `scrape_page_text`, `scrape_links`
- **Text Extraction & Analysis**: `extract_with_regex`, `extract_emails_urls`, `text_statistics`, `keyword_search`
- **Data Transformation**: `csv_parse`, `json_transform`, `merge_datasets`, `deduplicate`
- **Math & Analytics**: `calculate_stats`, `compare_values`
- **Encoding & Hashing**: `hash_data`, `encode_decode`, `validate_schema`
- **Date & Time**: `date_calc`
- **Formatting & Output**: `format_markdown_report`, `render_template`
- **PDF Processing**: `extract_pdf_text`
- **Memory** *(native — bypass sandbox)*: `memory_read`, `memory_write`, `memory_list`

**`memory.py`** — implements the three memory tools. Reads/writes `storage/memory/{agent_id}.json` — a flat JSON key-value store that persists across runs. Memory tools are always injected into the ReAct tool schema regardless of whether they appear in the agent's `tools` list.

---

## ReAct Execution Loop

The `react_agent` flow node type runs an autonomous loop — the LLM decides which tools to call at runtime rather than following a pre-wired sequence.

```
Pre-loop setup:
  1. _offload_large_inputs() — string values >2000 chars stored to memory, replaced with previews
  2. Memory tools (memory_read/write/list) injected into tool schema

Loop (up to max_iterations, default 30):
  1. build_scratchpad() — tiered rendering (full / summary / drop) with 6,000-char budget
  2. Build prompt: tool schemas + task + scratchpad
  3. Call LLMService → streamed tokens (or blocking for non-streaming providers)
  4. Parse response:
     - "ACTION" → _call_tool() (native or sandbox), append observation to scratchpad
     - "FINAL"  → store react_answer in output_data, break
     - "UNKNOWN" → inject correction message into scratchpad, retry
  5. _save_run() after every step (frontend sees live log updates)
```

Key design decisions:
- Tool input = `tool_args` only (for ReAct). Previous tool results are **not** merged in — they appear in the scratchpad for the LLM to read but don't pollute the tool's input dict.
- Recent scratchpad entries carry the **raw observation** so the model can re-use data as tool input. Only older entries are compressed.
- Native tools (`memory_*`) bypass the sandbox entirely — called directly via `NATIVE_TOOLS` dict.
- `_save_run()` is called after every LLM call and every tool execution so the frontend's run log updates in real time.

---

## DAG Flow Execution

When a flow has no `react_agent` node, `RunnerService._execute_run()` walks the DAG deterministically:

- `start` / `end` — bookkeeping only
- `tool_call` — executes the named tool via sandbox with `{**input_data, **tool_results}`
- `llm_call` — calls Ollama with a formatted prompt; result stored in `tool_results`
- `condition` — evaluates Python expression against `tool_results` and `input_data` to route to next node

---

## Frontend

Next.js App Router. All pages under `frontend/src/app/`.

### Pages

| Route | File | Purpose |
|---|---|---|
| `/` | `app/page.tsx` | Dashboard — list all agents |
| `/agents/new` | `app/agents/new/page.tsx` | Builder wizard |
| `/agents/[id]` | `app/agents/[id]/page.tsx` | Agent detail: Overview / Run / History tabs |
| `/agents/[id]/runs` | `app/agents/[id]/runs/page.tsx` | Run history for one agent |
| `/runs` | `app/runs/page.tsx` | Global run history |
| `/tool-runner` | `app/tool-runner/page.tsx` | Standalone tool tester |

### Key Components

**Builder wizard** (`components/builder/`):
- `WizardStepper` — step indicator (Config → Design → Validate → Review)
- `StepConfig` — name, description, model selection
- `StepDesign` — chat with LLM to generate system prompt and tools
- `StepValidate` — runs `validate_tools` against the sandbox, shows pass/fail per tool; `ToolEnhanceDialog` for LLM-assisted fixes
- `StepReview` — final review before `finalize`

**Run tab** (`components/runs/`):
- `AgentInputForm` — single textarea ("Describe what you want the agent to do"). Sends `{ task: "..." }` as input_data. Advanced toggle reveals raw JSON editor.
- `RunLog` — live log viewer, fed by SSE from `/api/runs/{id}/stream`
- `RunStatus` — status badge
- `RunHistory` — table of past runs with columns: Run ID, Status, Agent, Mode (ReAct/DAG/LLM chip), Steps, Tokens, Cost, Started, Duration
- `UsageStats` — displays per-run telemetry: input tokens, output tokens, cost, LLM call count, LLM latency, provider badge. Returns null when no usage data is present.

**Tool Runner** (`app/tool-runner/page.tsx`):
- Left panel: tools grouped by category, click to select
- Right panel: dynamic form built from `parameters` JSON Schema (string → text, number → number input, boolean → checkbox, array/object → JSON textarea with auto-parse)
- Output panel: shows result with field hints from `output_schema`; green/red status indicator

**Flow** (`components/flow/FlowVisualization.tsx`) — renders the DAG visually.

### API Client (`frontend/src/lib/api.ts`)

All calls to `http://localhost:8000`. Key functions:
- `getAgents`, `getAgent`, `updateAgent`, `deleteAgent`
- `startBuilder`, `sendBuilderMessage`, `generateFlow`, `finalizeAgent`
- `validateTools`, `enhanceTool`
- `startRun`, `getRun`, `getRuns`, `cancelRun`
- `getToolLibrary`, `getToolDetail`, `runTool`
- `getModels`
- `getSettings`, `saveSettings`

### Hooks (`frontend/src/lib/hooks/`)
- `useAgent(id)` — fetches and caches agent definition
- `useRun(runId)` — connects SSE stream; handles `log`, `status`, `live`, and `done` events. Returns `{ run, liveOutput, connected, error }`. `liveOutput` carries the in-progress token stream for display while a run is active.
- `useChat(agentId)` — manages builder conversation state
- `useModels()` — fetches available Ollama models

---

## Data Flow: Running an Agent

```
User types task → AgentInputForm → { task: "..." }
  → POST /api/runs → RunnerService.start_run()
    → asyncio.Task: _execute_run()
      → walks FlowDefinition nodes
        → tool_call: sandbox subprocess → result in tool_results
        → llm_call: LLMService.chat_stream() → tokens to _live_streams[run_id]
        → react_agent: ReAct loop (LLMService + tools, up to 30 iterations)
      → _save_run() on every step
      → ChatResult aggregated into run.usage (tokens, cost, latency)
  → SSE /api/runs/{id}/stream (250ms poll cadence):
      event: log    → new RunLog entry appended
      event: status → run fields updated (usage, llm_calls, provider, …)
      event: live   → current token stream (in-progress LLM response)
      event: done   → final RunResult; live buffer cleared
  → useRun hook drives RunLog + liveOutput + UsageStats components
```

---

## Data Flow: Building an Agent

```
User fills name/description → POST /api/builder/start → AgentDefinition created (status: draft)
  → Wizard steps call POST /api/builder/{id}/message with phase param:
    - phase=refine_prompt → system prompt generated + saved
    - phase=suggest_tools → tool list generated (prebuilt preferred)
    - phase=generate_tool_code per tool → code generated, self-validated, saved
  → POST /api/builder/{id}/generate-flow → linear DAG auto-built from tools
  → StepValidate: POST /api/builder/{id}/validate-tools → sandbox smoke test
  → POST /api/builder/{id}/finalize → status set to "ready"
```

---

## Storage Layout

```
storage/
  agents/
    {agent_id}.json        # AgentDefinition (includes tool code inline)
  runs/
    {run_id}.json          # RunResult (includes all logs + usage telemetry)
  memory/
    {agent_id}.json        # Persistent key-value store for memory_read/write/list
  settings.json            # Provider config, API keys, temperature, max_tokens
```

All persistence is synchronous file I/O via Pydantic `model_dump_json` / `model_validate_json`. No database.

---

## Programmatic Agent Creation

Agents can be created directly via the API without going through the builder wizard — useful for scripting, testing, and AI-assisted agent authoring.

```
POST /api/agents   body: AgentDefinition (full)
  → AgentService.create_full_agent()
    → writes storage/agents/{id}/agent.json
  → returns AgentDefinition with assigned id

POST /api/runs     body: { agent_id, input_data }
  → RunnerService.start_run()
    → asyncio.Task: _execute_run()
  → GET /api/runs/{run_id}  polls for status + logs
```

**Workflow for scripted agents:**
1. Construct an `AgentDefinition` dict — set `status: "ready"`, include full tool code and a flow with the desired node types.
2. `POST /api/agents` → receive `agent_id`.
3. `POST /api/runs` with `agent_id` and `input_data`.
4. Poll `GET /api/runs/{run_id}` until status is `completed` or `failed`.
5. Read `output_data` and `logs` from the run result.

See `test_react.py`, `test_react2.py`, and `test_react3.py` for working examples using pre-built tools in a `react_agent` flow.

---

## Known Constraints

- **Context window**: Local Ollama models typically have 4k–8k token context. The tiered scratchpad (full → summary → drop) and 6,000-char budget keep context bounded, but very long-running pipelines may still lose early observations.
- **ReAct format compliance**: Smaller models (< 7B) may deviate from the strict `Thought/Action/Input` format. The engine retries with a correction nudge on parse failure.
- **Model speed**: Local inference with larger models (e.g. `qwen3-vl:8b`) runs at ~60–120 seconds per LLM call on CPU. Long pipelines can take 10–20 minutes end-to-end.
- **Sandbox is not a true VM**: The subprocess + import blocklist is defense-in-depth, not a security boundary. Do not run untrusted user-submitted tool code in production.
- **Token streaming**: All LLM calls use `chat_stream()`. Tokens are buffered in `_live_streams[run_id]` and emitted as SSE `live` events every 250ms. The frontend renders the partial response live. Anthropic and OpenAI providers expose token counts through streaming; Ollama exposes them in the final chunk.
- **Single-process**: All runs execute as `asyncio.Task` in the same FastAPI process. Heavy concurrent runs will contend.
- **Memory is flat JSON**: The per-agent key-value store has no TTL, namespacing, or size limit. Large values stored via `memory_write` persist indefinitely until explicitly overwritten.
