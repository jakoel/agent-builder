"""Router for the pre-built tool library."""

from __future__ import annotations

from typing import Any, List

from fastapi import APIRouter, HTTPException

from ..tool_library.registry import get_catalog, get_tool_detail

router = APIRouter(prefix="/api/tool-library", tags=["tool-library"])


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
