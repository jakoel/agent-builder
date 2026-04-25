from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ..config import settings
from ..schemas.agent import AgentDefinition, FlowDefinition, ToolDefinition


class AgentService:
    """Persistence layer for agent definitions stored as JSON on disk."""

    def __init__(self, storage_path: Optional[Path] = None) -> None:
        self._base = (storage_path or settings.STORAGE_PATH) / "agents"
        self._base.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _agent_dir(self, agent_id: str) -> Path:
        return self._base / agent_id

    def _agent_file(self, agent_id: str) -> Path:
        return self._agent_dir(agent_id) / "agent.json"

    def _read(self, agent_id: str) -> AgentDefinition:
        path = self._agent_file(agent_id)
        if not path.exists():
            raise FileNotFoundError(f"Agent {agent_id} not found")
        return AgentDefinition.model_validate_json(path.read_text())

    def _write(self, agent_def: AgentDefinition) -> None:
        path = self._agent_file(agent_def.id)
        path.write_text(agent_def.model_dump_json(indent=2))

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_full_agent(self, agent_def: AgentDefinition) -> AgentDefinition:
        if not agent_def.id:
            agent_def = agent_def.model_copy(update={"id": uuid.uuid4().hex[:12]})
        agent_dir = self._agent_dir(agent_def.id)
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "tools").mkdir(exist_ok=True)
        now = datetime.utcnow()
        agent_def = agent_def.model_copy(update={"created_at": now, "updated_at": now})
        self._write(agent_def)
        return agent_def

    async def create_agent(
        self, name: str, description: str, model: Optional[str] = None
    ) -> AgentDefinition:
        agent_id = uuid.uuid4().hex[:12]
        agent_dir = self._agent_dir(agent_id)
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "tools").mkdir(exist_ok=True)

        now = datetime.utcnow()
        agent_def = AgentDefinition(
            id=agent_id,
            name=name,
            description=description,
            model=model or settings.DEFAULT_MODEL,
            created_at=now,
            updated_at=now,
        )
        self._write(agent_def)
        return agent_def

    async def get_agent(self, agent_id: str) -> AgentDefinition:
        return self._read(agent_id)

    async def list_agents(self) -> list[AgentDefinition]:
        agents: list[AgentDefinition] = []
        if not self._base.exists():
            return agents
        for child in sorted(self._base.iterdir()):
            agent_file = child / "agent.json"
            if child.is_dir() and agent_file.exists():
                try:
                    agents.append(AgentDefinition.model_validate_json(agent_file.read_text()))
                except Exception:
                    continue
        return agents

    async def update_agent(self, agent_id: str, updates: dict[str, Any]) -> AgentDefinition:
        agent_def = self._read(agent_id)
        update_data = agent_def.model_dump()
        update_data.update(updates)
        update_data["updated_at"] = datetime.utcnow()
        agent_def = AgentDefinition.model_validate(update_data)
        self._write(agent_def)
        return agent_def

    async def delete_agent(self, agent_id: str) -> None:
        agent_dir = self._agent_dir(agent_id)
        if agent_dir.exists():
            shutil.rmtree(agent_dir)

    # ------------------------------------------------------------------
    # Artifacts
    # ------------------------------------------------------------------

    async def save_tool_code(self, agent_id: str, tool: ToolDefinition) -> None:
        tools_dir = self._agent_dir(agent_id) / "tools"
        tools_dir.mkdir(parents=True, exist_ok=True)
        (tools_dir / tool.filename).write_text(tool.code)

    async def save_flow(self, agent_id: str, flow: FlowDefinition) -> None:
        path = self._agent_dir(agent_id) / "flow.json"
        path.write_text(flow.model_dump_json(indent=2))

    async def save_builder_history(
        self, agent_id: str, messages: list[dict[str, Any]]
    ) -> None:
        path = self._agent_dir(agent_id) / "builder_history.json"
        path.write_text(json.dumps(messages, indent=2, default=str))
