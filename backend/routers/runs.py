"""Run management router with SSE streaming support."""

from __future__ import annotations

import asyncio
import json
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from ..schemas.run import RunRequest, RunResult
from ..services.agent_service import AgentService
from ..services.llm_service import LLMService
from ..services.runner_service import RunnerService
from ..services.sandbox_service import SandboxService

router = APIRouter(prefix="/api/runs", tags=["runs"])

_llm = LLMService()
_agent_svc = AgentService()
_sandbox = SandboxService()
_runner_svc = RunnerService(_agent_svc, _llm, _sandbox)


@router.post("/", response_model=RunResult)
async def start_run(body: RunRequest) -> RunResult:
    try:
        return await _runner_svc.start_run(body.agent_id, body.input_data)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Agent not found")


@router.get("/", response_model=List[RunResult])
async def list_runs(agent_id: Optional[str] = Query(default=None)) -> list[RunResult]:
    return await _runner_svc.list_runs(agent_id=agent_id)


@router.get("/{run_id}", response_model=RunResult)
async def get_run(run_id: str) -> RunResult:
    try:
        return await _runner_svc.get_run(run_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Run not found")


@router.post("/{run_id}/cancel", response_model=RunResult)
async def cancel_run(run_id: str) -> RunResult:
    try:
        return await _runner_svc.cancel_run(run_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Run not found")


@router.get("/{run_id}/stream")
async def stream_run(run_id: str) -> StreamingResponse:
    """SSE endpoint that polls the run JSON every 500ms and yields status events."""

    try:
        await _runner_svc.get_run(run_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Run not found")

    async def _event_generator():
        last_log_count = 0
        last_live = ""
        while True:
            try:
                result = await _runner_svc.get_run(run_id)
            except FileNotFoundError:
                yield f"event: error\ndata: {json.dumps({'error': 'Run not found'})}\n\n"
                break

            # New log entries
            current_logs = result.logs
            if len(current_logs) > last_log_count:
                for log_entry in current_logs[last_log_count:]:
                    yield f"event: log\ndata: {log_entry.model_dump_json()}\n\n"
                last_log_count = len(current_logs)

            # Live LLM output (in-memory, updated chunk-by-chunk)
            live = _runner_svc.get_live_output(run_id) or ""
            if live != last_live:
                yield f"event: live\ndata: {json.dumps({'text': live})}\n\n"
                last_live = live

            # Status + usage snapshot
            status_payload = {
                "run_id": result.run_id,
                "status": result.status,
                "current_node": result.current_node,
                "usage": result.usage.model_dump(),
                "llm_calls": result.llm_calls,
                "total_llm_latency_ms": result.total_llm_latency_ms,
                "provider": result.provider,
            }
            yield f"event: status\ndata: {json.dumps(status_payload)}\n\n"

            if result.status in ("completed", "failed", "cancelled"):
                # Clear live buffer and emit final snapshot
                yield f"event: live\ndata: {json.dumps({'text': ''})}\n\n"
                final_payload = result.model_dump_json()
                yield f"event: done\ndata: {final_payload}\n\n"
                break

            await asyncio.sleep(0.25)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
