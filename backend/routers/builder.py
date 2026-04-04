"""Conversational agent-builder router."""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..schemas.agent import AgentDefinition
from ..schemas.builder import BuilderMessage, BuilderSession, EnhanceToolRequest
from ..services.agent_service import AgentService
from ..services.builder_service import BuilderService
from ..services.ollama_service import OllamaService
from ..services.sandbox_service import SandboxService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/builder", tags=["builder"])

_ollama = OllamaService()
_agent_svc = AgentService()
_sandbox_svc = SandboxService()
_builder_svc = BuilderService(_ollama, _agent_svc, _sandbox_svc)


class StartRequest(BaseModel):
    name: str
    description: str = ""
    model: Optional[str] = None


class MessageRequest(BaseModel):
    message: str
    phase: str = "chat"
    context: Optional[dict[str, Any]] = None


@router.post("/start", response_model=BuilderSession)
async def start_session(body: StartRequest) -> BuilderSession:
    return await _builder_svc.start_session(
        name=body.name, description=body.description, model=body.model
    )


@router.post("/{agent_id}/message", response_model=BuilderMessage)
async def process_message(agent_id: str, body: MessageRequest) -> BuilderMessage:
    try:
        return await _builder_svc.process_message(
            agent_id,
            body.message,
            phase=body.phase,
            context=body.context,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Agent not found")
    except Exception as exc:
        logger.exception("Builder message error")
        detail = str(exc) or f"{type(exc).__name__}: {repr(exc)}"
        raise HTTPException(status_code=500, detail=detail)


@router.post("/{agent_id}/finalize", response_model=AgentDefinition)
async def finalize_agent(agent_id: str) -> AgentDefinition:
    try:
        return await _builder_svc.finalize(agent_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Agent not found")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/{agent_id}/generate-flow")
async def generate_flow(agent_id: str):
    try:
        flow = await _builder_svc.generate_flow(agent_id)
        return flow.model_dump()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Agent not found")


@router.post("/{agent_id}/validate-tools")
async def validate_tools(agent_id: str):
    try:
        return await _builder_svc.validate_tools(agent_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Agent not found")


@router.post("/{agent_id}/enhance-tool")
async def enhance_tool(agent_id: str, body: EnhanceToolRequest):
    try:
        return await _builder_svc.enhance_tool(
            agent_id, body.tool_name, body.instruction
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Agent not found")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
