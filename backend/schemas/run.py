from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    agent_id: str
    input_data: dict[str, Any] = Field(default_factory=dict)


class RunLog(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    node_id: str
    message: str
    level: str = "info"


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0


class RunResult(BaseModel):
    run_id: str
    agent_id: str
    status: Literal["pending", "running", "completed", "failed", "cancelled"] = "pending"
    current_node: Optional[str] = None
    logs: list[RunLog] = Field(default_factory=list)
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    usage: TokenUsage = Field(default_factory=TokenUsage)
    llm_calls: int = 0
    total_llm_latency_ms: float = 0.0
    provider: Optional[str] = None


# Alias for compatibility
RunStatus = RunResult
