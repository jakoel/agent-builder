from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Optional

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from ..schemas.agent import ToolDefinition


class BuilderMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    artifacts: Optional[dict[str, Any]] = Field(
        default=None,
        description="Structured artifacts: system_prompt, tools, flow",
    )


class BuilderSession(BaseModel):
    agent_id: str
    messages: list[BuilderMessage] = Field(default_factory=list)
    status: str = "active"


class ToolValidationResult(BaseModel):
    tool_name: str
    status: Literal["pass", "fail"]
    error: Optional[str] = None
    output: Optional[Any] = None


class ValidateToolsResponse(BaseModel):
    results: list  # list of ToolValidationResult
    all_passed: bool


class EnhanceToolRequest(BaseModel):
    tool_name: str
    instruction: str


class EnhanceToolResponse(BaseModel):
    tool: Any  # ToolDefinition
    explanation: str
