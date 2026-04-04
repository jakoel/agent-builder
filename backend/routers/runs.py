"""Run management router with SSE streaming support."""

from __future__ import annotations

import asyncio
import json
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from ..schemas.run import RunRequest, RunResult
from ..services.agent_service import AgentService
from ..services.ollama_service import OllamaService
from ..services.runner_service import RunnerService
from ..services.sandbox_service import SandboxService

router = APIRouter(prefix="/api/runs", tags=["runs"])

_ollama = OllamaService()
_agent_svc = AgentService()
_sandbox = SandboxService()
_runner_svc = RunnerService(_agent_svc, _ollama, _sandbox)


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
        while True:
            try:
                result = await _runner_svc.get_run(run_id)
            except FileNotFoundError:
                yield f"event: error\ndata: {json.dumps({'error': 'Run not found'})}\n\n"
                break

            # Emit new log entries
            current_logs = result.logs
            if len(current_logs) > last_log_count:
                for log_entry in current_logs[last_log_count:]:
                    yield f"event: log\ndata: {log_entry.model_dump_json()}\n\n"
                last_log_count = len(current_logs)

            # Emit status
            status_payload = {
                "run_id": result.run_id,
                "status": result.status,
                "current_node": result.current_node,
            }
            yield f"event: status\ndata: {json.dumps(status_payload)}\n\n"

            if result.status in ("completed", "failed", "cancelled"):
                final_payload = result.model_dump_json()
                yield f"event: done\ndata: {final_payload}\n\n"
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
