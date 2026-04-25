"""Router for the pre-built tool library."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..tool_library.registry import NATIVE_TOOLS, get_catalog, get_tool_detail
from ..services.sandbox_service import SandboxService

router = APIRouter(prefix="/api/tool-library", tags=["tool-library"])

_sandbox = SandboxService()


class ToolRunRequest(BaseModel):
    input_data: Dict[str, Any] = {}


@router.get("/", response_model=List[dict])
async def list_tools() -> list[dict[str, Any]]:
    """Return all available pre-built tools (metadata only, no code)."""
    return get_catalog()


@router.get("/{tool_name}")
async def get_tool(tool_name: str) -> dict[str, Any]:
    """Return full tool detail including source code."""
    detail = get_tool_detail(tool_name)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    return detail


@router.post("/{tool_name}/run")
async def run_tool(tool_name: str, body: ToolRunRequest) -> dict[str, Any]:
    """Execute a pre-built tool with the given input and return its output."""
    detail = get_tool_detail(tool_name)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    try:
        native_fn = NATIVE_TOOLS.get(tool_name)
        if native_fn is not None:
            from ..config import settings
            output = native_fn(body.input_data, settings.STORAGE_PATH, "__tool_runner__")
        else:
            code = detail.get("code", "")
            output = await _sandbox.execute_tool(code=code, input_data=body.input_data)
        return {"status": "ok", "output": output}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
