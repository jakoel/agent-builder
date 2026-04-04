# Agent Builder Platform

Build, configure, and run AI agents through a chat-based interface. Powered by Ollama for LLM capabilities and LangGraph for agent orchestration.

## Architecture

- **Frontend**: Next.js (App Router, TypeScript, Tailwind CSS)
- **Backend**: FastAPI (Python, async)
- **LLM**: Ollama (local models)
- **Agent Runtime**: LangGraph with sandboxed tool execution

## Quick Start

```bash
# 1. Start Ollama
ollama serve

# 2. Pull a model
ollama pull llama3.1

# 3. Run setup
./setup.sh

# 4. Start backend
cd backend && uvicorn main:app --reload --port 8000

# 5. Start frontend (in another terminal)
cd frontend && npm run dev
```

Open http://localhost:3000 to access the platform.

## Project Structure

```
agentic_project/
├── frontend/          # Next.js UI
├── backend/           # FastAPI backend
├── storage/           # File-based persistence (agents, runs)
└── setup.sh           # Setup script
```

## Creating an Agent

1. Click "New Agent" in the sidebar
2. Enter a name, description, and select a model
3. Describe what you want the agent to do in the chat
4. The LLM generates system prompts, tools, and flow definitions
5. Review and edit the generated artifacts
6. Click "Finalize" to make the agent ready

## Running an Agent

1. Navigate to an agent's detail page
2. Go to the "Run" tab
3. Provide input data as JSON
4. Click "Run Agent"
5. Watch real-time logs via SSE streaming
