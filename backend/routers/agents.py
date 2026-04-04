"""CRUD router for agent definitions."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from ..schemas.agent import AgentDefinition
from ..services.agent_service import AgentService

router = APIRouter(prefix="/api/agents", tags=["agents"])

_agent_svc = AgentService()


@router.get("/", response_model=List[AgentDefinition])
async def list_agents() -> list[AgentDefinition]:
    return await _agent_svc.list_agents()


@router.get("/{agent_id}", response_model=AgentDefinition)
async def get_agent(agent_id: str) -> AgentDefinition:
    try:
        return await _agent_svc.get_agent(agent_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Agent not found")


@router.put("/{agent_id}", response_model=AgentDefinition)
async def update_agent(agent_id: str, body: dict[str, Any]) -> AgentDefinition:
    try:
        return await _agent_svc.update_agent(agent_id, body)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Agent not found")


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str) -> dict[str, str]:
    try:
        await _agent_svc.get_agent(agent_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Agent not found")
    await _agent_svc.delete_agent(agent_id)
    return {"status": "deleted", "agent_id": agent_id}
