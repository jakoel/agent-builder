"""Generic agent execution state used across the engine."""

from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    input_data: dict[str, Any]
    current_node: str
    messages: list[str]
    tool_results: dict[str, Any]
    output_data: dict[str, Any]
    error: str
