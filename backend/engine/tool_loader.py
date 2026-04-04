"""Dynamically create async callables from ToolDefinition objects."""

from __future__ import annotations

from typing import Any, Callable, Coroutine

from ..schemas.agent import ToolDefinition
from ..services.sandbox_service import SandboxService


def load_tool(
    tool_def: ToolDefinition,
    sandbox: SandboxService | None = None,
) -> Callable[..., Coroutine[Any, Any, dict[str, Any]]]:
    """Return an async function that executes *tool_def* via the sandbox."""
    _sandbox = sandbox or SandboxService()

    async def _run(input_data: dict[str, Any]) -> dict[str, Any]:
        return await _sandbox.execute_tool(code=tool_def.code, input_data=input_data)

    _run.__name__ = tool_def.name
    _run.__doc__ = tool_def.description
    return _run


def load_tools(
    tools: list[ToolDefinition],
    sandbox: SandboxService | None = None,
) -> dict[str, Callable[..., Coroutine[Any, Any, dict[str, Any]]]]:
    """Return a mapping of ``name -> async callable`` for every tool."""
    _sandbox = sandbox or SandboxService()
    return {t.name: load_tool(t, _sandbox) for t in tools}
