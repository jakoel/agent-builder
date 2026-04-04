from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ..config import settings
from ..schemas.agent import AgentDefinition
from ..schemas.run import RunLog, RunResult
from .agent_service import AgentService
from .ollama_service import OllamaService
from .sandbox_service import SandboxService

logger = logging.getLogger(__name__)


class RunnerService:
    """Manages agent run lifecycle: start, track, cancel."""

    def __init__(
        self,
        agent_svc: AgentService,
        ollama: OllamaService,
        sandbox: SandboxService,
    ) -> None:
        self._agent_svc = agent_svc
        self._ollama = ollama
        self._sandbox = sandbox
        self._runs_dir: Path = settings.STORAGE_PATH / "runs"
        self._runs_dir.mkdir(parents=True, exist_ok=True)
        self._active_tasks: dict[str, asyncio.Task[None]] = {}

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _run_file(self, run_id: str) -> Path:
        return self._runs_dir / f"{run_id}.json"

    def _save_run(self, result: RunResult) -> None:
        self._run_file(result.run_id).write_text(result.model_dump_json(indent=2))

    def _load_run(self, run_id: str) -> RunResult:
        path = self._run_file(run_id)
        if not path.exists():
            raise FileNotFoundError(f"Run {run_id} not found")
        return RunResult.model_validate_json(path.read_text())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start_run(
        self, agent_id: str, input_data: dict[str, Any]
    ) -> RunResult:
        agent_def = await self._agent_svc.get_agent(agent_id)

        run_id = uuid.uuid4().hex[:16]
        result = RunResult(
            run_id=run_id,
            agent_id=agent_id,
            status="pending",
            started_at=datetime.utcnow(),
        )
        self._save_run(result)

        task = asyncio.create_task(self._execute_run(run_id, agent_def, input_data))
        self._active_tasks[run_id] = task

        # Remove from active tasks when done
        task.add_done_callback(lambda _t: self._active_tasks.pop(run_id, None))

        return result

    async def get_run(self, run_id: str) -> RunResult:
        return self._load_run(run_id)

    async def list_runs(self, agent_id: Optional[str] = None) -> list[RunResult]:
        results: list[RunResult] = []
        for path in sorted(self._runs_dir.glob("*.json")):
            try:
                r = RunResult.model_validate_json(path.read_text())
                if agent_id is None or r.agent_id == agent_id:
                    results.append(r)
            except Exception:
                continue
        return results

    async def cancel_run(self, run_id: str) -> RunResult:
        task = self._active_tasks.get(run_id)
        if task and not task.done():
            task.cancel()
        result = self._load_run(run_id)
        result.status = "cancelled"
        result.completed_at = datetime.utcnow()
        self._save_run(result)
        return result

    # ------------------------------------------------------------------
    # Execution engine
    # ------------------------------------------------------------------

    async def _execute_run(
        self,
        run_id: str,
        agent_def: AgentDefinition,
        input_data: dict[str, Any],
    ) -> None:
        result = self._load_run(run_id)
        result.status = "running"
        self._save_run(result)

        try:
            flow = agent_def.flow
            if flow is None:
                # No flow -- just do a single LLM call
                result = await self._simple_llm_run(result, agent_def, input_data)
                return

            # Build lookup tables
            node_map = {n.id: n for n in flow.nodes}
            edge_map: dict[str, list] = {}
            for e in flow.edges:
                edge_map.setdefault(e.source, []).append(e)

            tool_map = {t.name: t for t in agent_def.tools}
            current_id = flow.entry_node
            messages: list[dict[str, str]] = []
            tool_results: dict[str, Any] = {}

            while current_id:
                node = node_map.get(current_id)
                if node is None:
                    raise ValueError(f"Node {current_id} not found in flow")

                result.current_node = current_id
                self._save_run(result)

                if node.type == "start":
                    self._log(result, node.id, "Starting agent run")
                elif node.type == "end":
                    self._log(result, node.id, "Run completed")
                    break
                elif node.type == "tool_call":
                    tool_def = tool_map.get(node.tool_name or "")
                    if tool_def is None:
                        raise ValueError(f"Tool '{node.tool_name}' not found")
                    self._log(result, node.id, f"Executing tool: {node.tool_name}")
                    sandbox_input = {**input_data, **tool_results}
                    res = await self._sandbox.execute_tool(
                        code=tool_def.code, input_data=sandbox_input
                    )
                    tool_results[node.tool_name or node.id] = res
                    self._log(result, node.id, f"Tool result: {json.dumps(res)[:500]}")
                elif node.type == "llm_call":
                    prompt = (node.prompt_template or "{input}").format(
                        input=json.dumps(input_data),
                        tool_results=json.dumps(tool_results),
                        **input_data,
                    )
                    messages.append({"role": "user", "content": prompt})
                    self._log(result, node.id, "Calling LLM")
                    llm_resp = await self._ollama.chat(
                        model=agent_def.model,
                        messages=messages,
                        system=agent_def.system_prompt or None,
                    )
                    messages.append({"role": "assistant", "content": llm_resp})
                    tool_results[f"llm_{node.id}"] = llm_resp
                    self._log(result, node.id, f"LLM response: {llm_resp[:500]}")
                elif node.type == "condition":
                    self._log(result, node.id, "Evaluating condition")

                self._save_run(result)

                # Determine next node
                edges = edge_map.get(current_id, [])
                if not edges:
                    break

                next_id = None
                if node.type == "condition" and len(edges) > 1:
                    # Evaluate edge conditions against tool_results
                    for edge in edges:
                        if edge.condition:
                            try:
                                if eval(  # noqa: S307
                                    edge.condition,
                                    {"__builtins__": {}},
                                    {"tool_results": tool_results, "input_data": input_data},
                                ):
                                    next_id = edge.target
                                    break
                            except Exception:
                                continue
                    if next_id is None:
                        # Fallback to first edge without condition or last edge
                        fallback = [e for e in edges if not e.condition]
                        next_id = (fallback[0] if fallback else edges[-1]).target
                else:
                    next_id = edges[0].target

                current_id = next_id

            result.status = "completed"
            result.output_data = tool_results
            result.completed_at = datetime.utcnow()

        except asyncio.CancelledError:
            result.status = "cancelled"
            result.completed_at = datetime.utcnow()
        except Exception as exc:
            logger.exception("Run %s failed", run_id)
            result.status = "failed"
            result.error = str(exc)
            result.completed_at = datetime.utcnow()
        finally:
            self._save_run(result)

    async def _simple_llm_run(
        self,
        result: RunResult,
        agent_def: AgentDefinition,
        input_data: dict[str, Any],
    ) -> RunResult:
        """Fallback when no flow is defined: single LLM call."""
        self._log(result, "llm", "No flow defined -- running single LLM call")
        try:
            messages = [{"role": "user", "content": json.dumps(input_data)}]
            llm_resp = await self._ollama.chat(
                model=agent_def.model,
                messages=messages,
                system=agent_def.system_prompt or None,
            )
            result.output_data = {"response": llm_resp}
            result.status = "completed"
        except Exception as exc:
            result.status = "failed"
            result.error = str(exc)
        result.completed_at = datetime.utcnow()
        self._save_run(result)
        return result

    def _log(self, result: RunResult, node_id: str, message: str) -> None:
        result.logs.append(
            RunLog(timestamp=datetime.utcnow(), node_id=node_id, message=message)
        )
