from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ..config import settings
from ..engine.react_engine import (
    REACT_SYSTEM,
    REACT_PROMPT_TEMPLATE,
    build_scratchpad,
    format_tool_schemas,
    parse_react_response,
)
from ..schemas.agent import AgentDefinition, FlowNode
from ..schemas.run import RunLog, RunResult
from ..tool_library.registry import NATIVE_TOOLS, TOOL_CATALOG
from ..tool_library.memory import memory_write
from .agent_service import AgentService
from .llm_service import ChatResult, LLMService
from .sandbox_service import SandboxService
from . import settings_service

logger = logging.getLogger(__name__)


class RunnerService:
    """Manages agent run lifecycle: start, track, cancel."""

    def __init__(
        self,
        agent_svc: AgentService,
        llm: LLMService,
        sandbox: SandboxService,
    ) -> None:
        self._agent_svc = agent_svc
        self._llm = llm
        self._sandbox = sandbox
        self._runs_dir: Path = settings.STORAGE_PATH / "runs"
        self._runs_dir.mkdir(parents=True, exist_ok=True)
        self._active_tasks: dict[str, asyncio.Task[None]] = {}
        # In-memory live LLM output buffers keyed by run_id (cleared after each call)
        self._live_streams: dict[str, str] = {}
        # Run IDs cancelled by the watchdog (distinguished from user cancels)
        self._timed_out_runs: set[str] = set()

    # ------------------------------------------------------------------
    # Live streaming (in-memory only)
    # ------------------------------------------------------------------

    def get_live_output(self, run_id: str) -> Optional[str]:
        return self._live_streams.get(run_id)

    def _set_live(self, run_id: str, text: str) -> None:
        self._live_streams[run_id] = text

    def _clear_live(self, run_id: str) -> None:
        self._live_streams.pop(run_id, None)

    async def _stream_chat(
        self,
        run_id: str,
        result: RunResult,
        model: str,
        messages: list[dict[str, str]],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Stream an LLM call: live-update _live_streams[run_id] per chunk,
        aggregate usage into result, return full content."""
        accumulated = ""
        final: Optional[ChatResult] = None
        async for chunk, maybe_final in self._llm.chat_stream(
            model=model,
            messages=messages,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            if chunk:
                accumulated += chunk
                self._set_live(run_id, accumulated)
            if maybe_final is not None:
                final = maybe_final

        self._clear_live(run_id)

        if final is not None:
            result.usage.prompt_tokens += final.prompt_tokens
            result.usage.completion_tokens += final.completion_tokens
            result.usage.total_tokens += final.total_tokens
            result.usage.cost_usd += final.cost_usd
            result.llm_calls += 1
            result.total_llm_latency_ms += final.latency_ms
            result.provider = final.provider
            return final.content
        return accumulated

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
        self, agent_id: str, input_data: dict[str, Any], run_timeout_seconds: int = 600
    ) -> RunResult:
        agent_def = await self._agent_svc.get_agent(agent_id)

        run_id = uuid.uuid4().hex[:16]
        result = RunResult(
            run_id=run_id,
            agent_id=agent_id,
            status="pending",
            input_data=input_data,
            started_at=datetime.utcnow(),
            run_timeout_seconds=run_timeout_seconds,
        )
        self._save_run(result)

        task = asyncio.create_task(self._execute_run(run_id, agent_def, input_data))
        self._active_tasks[run_id] = task

        # Remove from active tasks when done
        task.add_done_callback(lambda _t: self._active_tasks.pop(run_id, None))

        return result

    async def start_watchdog(self) -> None:
        asyncio.create_task(self._watchdog_loop())

    async def _watchdog_loop(self) -> None:
        """Every 60s: force-fail runs that exceeded their timeout or whose task was lost."""
        while True:
            try:
                await asyncio.sleep(60)
                now = datetime.utcnow()
                for path in self._runs_dir.glob("*.json"):
                    try:
                        run = RunResult.model_validate_json(path.read_text())
                    except Exception:
                        continue
                    if run.status != "running":
                        continue
                    elapsed = (now - run.started_at).total_seconds()
                    task = self._active_tasks.get(run.run_id)
                    if task is None:
                        # Task lost (server restart while running)
                        run.status = "failed"
                        run.error = "run aborted: server restarted while running"
                        run.completed_at = now
                        path.write_text(run.model_dump_json(indent=2))
                    elif elapsed > run.run_timeout_seconds:
                        # Mark before cancelling so the CancelledError handler sees it
                        self._timed_out_runs.add(run.run_id)
                        task.cancel()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Watchdog error")

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

        cfg = settings_service.load()
        temperature: float = cfg.get("default_temperature", 0.7)
        max_tokens: int = cfg.get("default_max_tokens", 2048)

        try:
            flow = agent_def.flow
            if flow is None:
                # No flow -- just do a single LLM call
                result = await self._simple_llm_run(result, agent_def, input_data, temperature, max_tokens)
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
                    try:
                        res = await asyncio.wait_for(
                            self._call_tool(tool_def.name, tool_def.code, sandbox_input, agent_def.id),
                            timeout=node.node_timeout_seconds,
                        )
                    except asyncio.TimeoutError:
                        raise RuntimeError(
                            f"Node '{node.id}' (tool '{node.tool_name}') timed out after {node.node_timeout_seconds}s"
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
                    try:
                        llm_resp = await asyncio.wait_for(
                            self._stream_chat(
                                run_id,
                                result,
                                model=agent_def.model,
                                messages=messages,
                                system=agent_def.system_prompt or None,
                                temperature=temperature,
                                max_tokens=max_tokens,
                            ),
                            timeout=node.node_timeout_seconds,
                        )
                    except asyncio.TimeoutError:
                        raise RuntimeError(
                            f"Node '{node.id}' LLM call timed out after {node.node_timeout_seconds}s"
                        )
                    messages.append({"role": "assistant", "content": llm_resp})
                    tool_results[f"llm_{node.id}"] = llm_resp
                    self._log(result, node.id, f"LLM response: {llm_resp[:500]}")
                elif node.type == "condition":
                    self._log(result, node.id, "Evaluating condition")
                elif node.type == "react_agent":
                    react_out = await self._react_run(result, agent_def, node, input_data, temperature, max_tokens)
                    tool_results[node.id] = react_out

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
            if run_id in self._timed_out_runs:
                self._timed_out_runs.discard(run_id)
                result.status = "failed"
                result.error = f"run timeout after {result.run_timeout_seconds}s"
            else:
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
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> RunResult:
        """Fallback when no flow is defined: single LLM call."""
        self._log(result, "llm", "No flow defined -- running single LLM call")
        try:
            messages = [{"role": "user", "content": json.dumps(input_data)}]
            llm_resp = await self._stream_chat(
                result.run_id,
                result,
                model=agent_def.model,
                messages=messages,
                system=agent_def.system_prompt or None,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            result.output_data = {"response": llm_resp}
            result.status = "completed"
        except Exception as exc:
            result.status = "failed"
            result.error = str(exc)
        result.completed_at = datetime.utcnow()
        self._save_run(result)
        return result

    async def _react_run(
        self,
        result: RunResult,
        agent_def: AgentDefinition,
        node: FlowNode,
        input_data: dict[str, Any],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        # Offload large string inputs to memory; replace with compact references
        task_input = self._offload_large_inputs(input_data, agent_def.id)
        task = json.dumps(task_input)

        # Always make memory tools available in ReAct (needed to retrieve offloaded data)
        all_tools = list(agent_def.tools)
        existing_names = {t.name for t in all_tools}
        from ..schemas.agent import ToolDefinition
        for cat_entry in TOOL_CATALOG:
            if cat_entry["name"] in NATIVE_TOOLS and cat_entry["name"] not in existing_names:
                all_tools.append(ToolDefinition(
                    name=cat_entry["name"],
                    description=cat_entry["description"],
                    parameters=cat_entry["parameters"],
                    output_schema=cat_entry["output_schema"],
                    code="",
                    filename="__native__",
                ))

        tool_map = {t.name: t for t in all_tools}
        tool_descriptions = format_tool_schemas(all_tools)
        scratchpad_entries: list[dict[str, str]] = []

        tool_error_counts: dict[str, int] = {}
        MAX_TOOL_ERRORS = 5
        node_timeout = node.node_timeout_seconds

        for iteration in range(node.max_iterations):
            scratchpad = build_scratchpad(scratchpad_entries)
            prompt = REACT_PROMPT_TEMPLATE.format(
                tool_descriptions=tool_descriptions,
                task=task,
                scratchpad=scratchpad,
            )

            self._log(result, node.id, f"ReAct iteration {iteration + 1}/{node.max_iterations}")
            self._save_run(result)

            try:
                response = await asyncio.wait_for(
                    self._stream_chat(
                        result.run_id,
                        result,
                        model=agent_def.model,
                        messages=[{"role": "user", "content": prompt}],
                        system=REACT_SYSTEM,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    ),
                    timeout=node_timeout,
                )
            except asyncio.TimeoutError:
                raise RuntimeError(
                    f"ReAct LLM call timed out after {node_timeout}s on iteration {iteration + 1}"
                )
            self._log(result, node.id, f"LLM: {response[:400]}")

            kind, payload = parse_react_response(response)

            if kind == "FINAL":
                self._log(result, node.id, f"Final Answer: {payload}")
                return {"final_answer": payload, "iterations": iteration + 1}

            if kind == "ACTION":
                tool_name, tool_args = payload
                tool_def = tool_map.get(tool_name)
                is_native = tool_name in NATIVE_TOOLS
                if tool_def is None and not is_native:
                    obs_dict: dict[str, Any] = {
                        "error": "tool_not_found",
                        "tool": tool_name,
                        "detail": f"Available tools: {list(tool_map.keys())}",
                    }
                    observation = json.dumps(obs_dict)
                    tool_error_counts[tool_name] = tool_error_counts.get(tool_name, 0) + 1
                else:
                    self._log(result, node.id, f"Calling tool: {tool_name} args={json.dumps(tool_args)[:300]}")
                    try:
                        obs_raw = await asyncio.wait_for(
                            self._call_tool(
                                tool_name,
                                tool_def.code if tool_def else "",
                                tool_args,
                                agent_def.id,
                            ),
                            timeout=node_timeout,
                        )
                        observation = json.dumps(obs_raw)
                        tool_error_counts[tool_name] = 0
                    except asyncio.TimeoutError:
                        obs_dict = {
                            "error": "tool_timeout",
                            "tool": tool_name,
                            "detail": f"tool timed out after {node_timeout}s",
                        }
                        observation = json.dumps(obs_dict)
                        self._log(result, node.id, f"Tool timeout: {tool_name}", level="warning")
                        tool_error_counts[tool_name] = tool_error_counts.get(tool_name, 0) + 1
                    except Exception as exc:
                        obs_dict = {
                            "error": "tool_error",
                            "tool": tool_name,
                            "detail": str(exc),
                        }
                        observation = json.dumps(obs_dict)
                        self._log(result, node.id, f"Tool error: {tool_name}: {exc}", level="warning")
                        tool_error_counts[tool_name] = tool_error_counts.get(tool_name, 0) + 1

                    if tool_error_counts.get(tool_name, 0) >= MAX_TOOL_ERRORS:
                        raise RuntimeError(
                            f"Tool '{tool_name}' failed {MAX_TOOL_ERRORS} consecutive times; aborting run"
                        )

                self._log(result, node.id, f"Observation: {observation[:2000]}")
            else:
                observation = "Could not parse your response. Use the exact format: Thought / Action / Input or Final Answer."
                self._log(result, node.id, f"Parse failed: {response[:200]}")

            thought_text = ""
            if "Thought:" in response:
                thought_text = response.split("Thought:", 1)[1].split("Action:", 1)[0].strip()

            scratchpad_entries.append({
                "thought": thought_text,
                "action": payload[0] if kind == "ACTION" else "",
                "input": json.dumps(payload[1]) if kind == "ACTION" else "",
                "observation": observation,
            })

        self._log(result, node.id, f"Reached max iterations ({node.max_iterations})")
        return {"final_answer": "Max iterations reached without a final answer.", "iterations": node.max_iterations}

    LARGE_STRING_THRESHOLD = 2000  # chars — strings longer than this get offloaded to memory

    def _offload_large_inputs(self, input_data: dict[str, Any], agent_id: str) -> dict[str, Any]:
        """Store large string values in agent memory; replace with a compact reference."""
        result: dict[str, Any] = {}
        for k, v in input_data.items():
            if isinstance(v, str) and len(v) > self.LARGE_STRING_THRESHOLD:
                lines = v.strip().splitlines()
                preview = "\n".join(lines[:4])
                memory_write({"key": k, "value": v}, settings.STORAGE_PATH, agent_id)
                result[k] = (
                    f"[Data stored in agent memory under key='{k}' "
                    f"({len(lines)} lines). "
                    f"Call memory_read with key='{k}' to retrieve it. "
                    f"Preview (first 4 lines):\n{preview}"
                )
            else:
                result[k] = v
        return result

    async def _call_tool(
        self,
        tool_name: str,
        tool_code: str,
        input_data: dict[str, Any],
        agent_id: str,
    ) -> dict[str, Any]:
        native_fn = NATIVE_TOOLS.get(tool_name)
        if native_fn is not None:
            return native_fn(input_data, settings.STORAGE_PATH, agent_id)
        return await self._sandbox.execute_tool(code=tool_code, input_data=input_data)

    def _log(self, result: RunResult, node_id: str, message: str, level: str = "info") -> None:
        result.logs.append(
            RunLog(timestamp=datetime.utcnow(), node_id=node_id, message=message, level=level)
        )
