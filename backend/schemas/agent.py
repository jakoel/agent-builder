from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict, description="JSON Schema for tool parameters")
    code: str
    filename: str


class FlowNode(BaseModel):
    id: str
    label: str
    type: Literal["tool_call", "llm_call", "condition", "start", "end"]
    tool_name: Optional[str] = None
    prompt_template: Optional[str] = None


class FlowEdge(BaseModel):
    source: str
    target: str
    condition: Optional[str] = None


class FlowDefinition(BaseModel):
    nodes: list[FlowNode]
    edges: list[FlowEdge]
    entry_node: str


class AgentDefinition(BaseModel):
    id: str
    name: str
    description: str
    system_prompt: str = ""
    model: str = "llama3.1"
    tools: list[ToolDefinition] = Field(default_factory=list)
    flow: Optional[FlowDefinition] = None
    status: Literal["draft", "ready", "error"] = "draft"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
