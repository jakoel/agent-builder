from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from ..schemas.agent import (
    AgentDefinition,
    FlowDefinition,
    FlowEdge,
    FlowNode,
    ToolDefinition,
)
from ..schemas.builder import BuilderMessage, BuilderSession
from ..tool_library.registry import get_catalog
from .agent_service import AgentService
from .llm_service import LLMService
from .sandbox_service import SandboxService

logger = logging.getLogger(__name__)


def _build_prebuilt_catalog_text() -> str:
    """Format the prebuilt tool catalog for injection into LLM prompts."""
    lines = []
    for t in get_catalog():
        lines.append(f'- {t["name"]}: {t["description"]}')
    return "\n".join(lines)


PREBUILT_TOOLS_TEXT = _build_prebuilt_catalog_text()

# ---------------------------------------------------------------------------
# Phase-specific system prompts
# ---------------------------------------------------------------------------

REFINE_PROMPT_SYSTEM = """\
You are helping a user design the system prompt for an AI agent.
{draft_section}
Take the user's input and produce a refined, clear, well-structured system prompt.
Return ONLY the system prompt text. No JSON, no markdown fences, no extra commentary."""

SUGGEST_TOOLS_SYSTEM = """\
You are helping design tools for an AI agent with this system prompt:

---
{system_prompt}
---

The platform has these PRE-BUILT tools already available (tested and ready to use).
When a pre-built tool fits the need, prefer it over creating a new custom tool.
Mark pre-built tools with "prebuilt": true in your response.

Pre-built tools:
{prebuilt_catalog}
{current_tools_section}
Based on the conversation, suggest or update the list of tools this agent needs.
Return ONLY a valid JSON array where each element has:
- "name": snake_case function name (use the exact pre-built name if using a pre-built tool)
- "description": one-line description of what the tool does
- "parameters": JSON Schema object with "type": "object", "properties": {{}}, "required": []
- "prebuilt": true if this is a pre-built tool, false if it needs custom code

No markdown fences, no text outside the JSON array."""

GENERATE_TOOL_CODE_SYSTEM = """\
Generate a Python function for an AI agent tool.

Tool name: {tool_name}
Description: {tool_description}
Parameters: {tool_parameters}
{modification_section}
Rules:
- Function MUST be named `{tool_name}` and accept a single `input_data: dict` parameter
- MUST return a dict with the results
- Allowed imports: json, re, datetime, math, requests, bs4, urllib, collections, itertools, functools, hashlib, base64, html, csv, time, random, string, typing
- Do NOT use: os, sys, subprocess, socket, or any restricted module
- Handle errors gracefully by returning error info in the dict

Return ONLY Python code. No markdown fences, no explanation."""

# Legacy prompt kept for backward compatibility
META_PROMPT = """\
You are an expert agent architect. The user is building an AI agent.
Based on the conversation so far, generate a JSON object with the following keys:

- "system_prompt": a string with the system prompt for the agent
- "tools": a list of tool objects, each with:
    - "name": tool function name (snake_case)
    - "description": what the tool does
    - "parameters": JSON Schema dict describing the input
    - "code": complete Python function code for the tool (the function must be named the same as "name" and accept a single dict argument called `input_data`, returning a dict)
- "flow": an object with:
    - "nodes": list of {id, label, type, tool_name (if tool_call), prompt_template (if llm_call)}
      where type is one of: start, end, tool_call, llm_call, condition
    - "edges": list of {source, target, condition (optional)}
    - "entry_node": id of the first node

Return ONLY valid JSON. No markdown fences, no explanation outside the JSON.
"""


class BuilderService:
    """Orchestrates the conversational agent-building flow."""

    def __init__(
        self,
        llm: LLMService,
        agent_svc: AgentService,
        sandbox: Optional[SandboxService] = None,
    ) -> None:
        self._llm = llm
        self._agent_svc = agent_svc
        self._sandbox = sandbox or SandboxService()
        self._sessions: dict[str, BuilderSession] = {}

    async def _chat(self, **kwargs: Any) -> str:
        """Wizard-internal LLM call: returns content string only (usage discarded)."""
        result = await self._llm.chat(**kwargs)
        return result.content

    async def start_session(
        self, name: str, description: str, model: Optional[str] = None
    ) -> BuilderSession:
        agent_def = await self._agent_svc.create_agent(name, description, model)
        session = BuilderSession(agent_id=agent_def.id)
        self._sessions[agent_def.id] = session
        return session

    # ------------------------------------------------------------------
    # Main message handler (phase-aware)
    # ------------------------------------------------------------------

    async def process_message(
        self,
        agent_id: str,
        user_message: str,
        phase: str = "chat",
        context: Optional[dict[str, Any]] = None,
    ) -> BuilderMessage:
        context = context or {}
        agent_def = await self._agent_svc.get_agent(agent_id)

        if phase == "refine_prompt":
            return await self._refine_prompt(agent_id, agent_def, user_message, context)
        elif phase == "suggest_tools":
            return await self._suggest_tools(agent_id, agent_def, user_message, context)
        elif phase == "generate_tool_code":
            return await self._generate_tool_code(agent_id, agent_def, user_message, context)
        else:
            return await self._legacy_chat(agent_id, agent_def, user_message)

    # ------------------------------------------------------------------
    # Phase handlers
    # ------------------------------------------------------------------

    async def _refine_prompt(
        self,
        agent_id: str,
        agent_def: AgentDefinition,
        user_message: str,
        context: dict[str, Any],
    ) -> BuilderMessage:
        current_draft = context.get("current_draft", "")
        if current_draft:
            draft_section = f"\nCurrent draft:\n{current_draft}\n\nApply the user's feedback to improve it.\n"
        else:
            draft_section = "\nThis is the initial description from the user.\n"

        system = REFINE_PROMPT_SYSTEM.format(draft_section=draft_section)
        response = await self._chat(
            model=agent_def.model,
            messages=[{"role": "user", "content": user_message}],
            system=system,
        )
        refined = response.strip()

        # Persist the prompt
        await self._agent_svc.update_agent(agent_id, {"system_prompt": refined})

        return BuilderMessage(
            role="assistant",
            content=refined,
            artifacts={"system_prompt": refined},
        )

    async def _suggest_tools(
        self,
        agent_id: str,
        agent_def: AgentDefinition,
        user_message: str,
        context: dict[str, Any],
    ) -> BuilderMessage:
        system_prompt = context.get("system_prompt", agent_def.system_prompt or "")
        current_tools = context.get("current_tools", [])

        current_tools_section = ""
        if current_tools:
            current_tools_section = (
                f"\nCurrent tool list:\n{json.dumps(current_tools, indent=2)}\n"
                "Apply the user's requested changes.\n"
            )

        system = SUGGEST_TOOLS_SYSTEM.format(
            system_prompt=system_prompt,
            prebuilt_catalog=PREBUILT_TOOLS_TEXT,
            current_tools_section=current_tools_section,
        )
        response = await self._chat(
            model=agent_def.model,
            messages=[{"role": "user", "content": user_message}],
            system=system,
        )

        tools = self._parse_tool_list(response)
        return BuilderMessage(
            role="assistant",
            content=response,
            artifacts={"suggested_tools": tools} if tools else None,
        )

    async def _generate_tool_code(
        self,
        agent_id: str,
        agent_def: AgentDefinition,
        user_message: str,
        context: dict[str, Any],
    ) -> BuilderMessage:
        tool_name = context.get("tool_name", "tool")
        tool_description = context.get("tool_description", "")
        prebuilt_code = context.get("prebuilt_code", "")

        # If prebuilt code is provided, skip LLM generation entirely
        if prebuilt_code:
            code = prebuilt_code
            tool_def = ToolDefinition(
                name=tool_name,
                description=tool_description,
                parameters=context.get("tool_parameters", {}),
                code=code,
                filename=f"{tool_name}.py",
            )
            await self._agent_svc.save_tool_code(agent_id, tool_def)
            agent_def = await self._agent_svc.get_agent(agent_id)
            updated_tools = [t for t in agent_def.tools if t.name != tool_name]
            updated_tools.append(tool_def)
            await self._agent_svc.update_agent(
                agent_id, {"tools": [t.model_dump() for t in updated_tools]}
            )
            return BuilderMessage(
                role="assistant",
                content=code,
                artifacts={"tool": tool_def.model_dump()},
            )

        tool_parameters = json.dumps(context.get("tool_parameters", {}), indent=2)
        current_code = context.get("current_code", "")

        modification_section = ""
        if current_code:
            modification_section = (
                f"\nCurrent code:\n{current_code}\n\n"
                f"User requested modification: {user_message}\n"
            )

        system = GENERATE_TOOL_CODE_SYSTEM.format(
            tool_name=tool_name,
            tool_description=tool_description,
            tool_parameters=tool_parameters,
            modification_section=modification_section,
        )

        prompt_msg = (
            user_message
            if current_code
            else f"Generate the {tool_name} tool function."
        )
        response = await self._chat(
            model=agent_def.model,
            messages=[{"role": "user", "content": prompt_msg}],
            system=system,
        )

        code = self._clean_code(response)
        code = await self.self_validate_generated_code(code, agent_def.model)

        # Build and persist tool definition
        tool_def = ToolDefinition(
            name=tool_name,
            description=tool_description,
            parameters=context.get("tool_parameters", {}),
            code=code,
            filename=f"{tool_name}.py",
        )
        await self._agent_svc.save_tool_code(agent_id, tool_def)

        # Update the agent's tool list
        agent_def = await self._agent_svc.get_agent(agent_id)
        updated_tools = [t for t in agent_def.tools if t.name != tool_name]
        updated_tools.append(tool_def)
        await self._agent_svc.update_agent(
            agent_id, {"tools": [t.model_dump() for t in updated_tools]}
        )

        return BuilderMessage(
            role="assistant",
            content=code,
            artifacts={"tool": tool_def.model_dump()},
        )

    async def _legacy_chat(
        self,
        agent_id: str,
        agent_def: AgentDefinition,
        user_message: str,
    ) -> BuilderMessage:
        """Fallback to the old single-shot META_PROMPT approach."""
        session = self._sessions.get(agent_id)
        if session is None:
            session = BuilderSession(agent_id=agent_id)
            self._sessions[agent_id] = session

        user_msg = BuilderMessage(role="user", content=user_message)
        session.messages.append(user_msg)

        chat_messages = [
            {"role": m.role, "content": m.content} for m in session.messages
        ]
        raw_response = await self._chat(
            model=agent_def.model,
            messages=chat_messages,
            system=META_PROMPT,
        )

        artifacts = self._extract_artifacts(raw_response)
        if artifacts:
            await self._apply_artifacts(agent_id, artifacts)

        assistant_msg = BuilderMessage(
            role="assistant", content=raw_response, artifacts=artifacts
        )
        session.messages.append(assistant_msg)
        return assistant_msg

    # ------------------------------------------------------------------
    # Flow generation
    # ------------------------------------------------------------------

    async def generate_flow(self, agent_id: str) -> FlowDefinition:
        """Auto-generate a linear flow from the agent's tools."""
        agent_def = await self._agent_svc.get_agent(agent_id)
        flow = self._build_linear_flow(agent_def.tools)
        await self._agent_svc.save_flow(agent_id, flow)
        await self._agent_svc.update_agent(agent_id, {"flow": flow.model_dump()})
        return flow

    @staticmethod
    def _build_linear_flow(tools: list[ToolDefinition]) -> FlowDefinition:
        nodes = [FlowNode(id="start", label="Start", type="start")]
        edges: list[FlowEdge] = []

        prev_id = "start"
        for tool in tools:
            node_id = f"tool_{tool.name}"
            nodes.append(
                FlowNode(
                    id=node_id,
                    label=tool.name,
                    type="tool_call",
                    tool_name=tool.name,
                )
            )
            edges.append(FlowEdge(source=prev_id, target=node_id))
            prev_id = node_id

        nodes.append(FlowNode(id="end", label="End", type="end"))
        edges.append(FlowEdge(source=prev_id, target="end"))

        return FlowDefinition(nodes=nodes, edges=edges, entry_node="start")

    # ------------------------------------------------------------------
    # Finalize / validate / enhance (unchanged)
    # ------------------------------------------------------------------

    async def finalize(self, agent_id: str) -> AgentDefinition:
        agent_def = await self._agent_svc.get_agent(agent_id)

        errors: list[str] = []
        if not agent_def.system_prompt:
            errors.append("Missing system_prompt")
        if not agent_def.flow:
            errors.append("Missing flow definition")

        if errors:
            await self._agent_svc.update_agent(agent_id, {"status": "error"})
            raise ValueError(f"Agent validation failed: {'; '.join(errors)}")

        updated = await self._agent_svc.update_agent(agent_id, {"status": "ready"})
        return updated

    async def self_validate_generated_code(self, code: str, model: str) -> str:
        validation_prompt = (
            "Review this Python function for syntax errors, undefined variables, missing imports, "
            "and logic issues. The function must accept a single dict argument called `input_data` and return a dict. "
            "Only these imports are allowed: json, re, datetime, math, requests, bs4, urllib, collections, "
            "itertools, functools, hashlib, base64, html, csv, time, random, string, typing.\n\n"
            "If there are problems, return a CORRECTED version. If it's correct, return it unchanged.\n"
            "Return ONLY the Python code, no markdown fences, no explanation.\n\n"
            f"{code}"
        )
        corrected = await self._chat(
            model=model,
            messages=[{"role": "user", "content": validation_prompt}],
        )
        cleaned = self._clean_code(corrected)
        try:
            compile(cleaned, "<tool>", "exec")
            return cleaned
        except SyntaxError:
            return code

    async def validate_tools(self, agent_id: str):
        from ..schemas.builder import ToolValidationResult, ValidateToolsResponse

        agent_def = await self._agent_svc.get_agent(agent_id)
        results = []
        for tool in agent_def.tools:
            test_input = {}
            if tool.parameters and "properties" in tool.parameters:
                for prop_name, prop_schema in tool.parameters["properties"].items():
                    prop_type = prop_schema.get("type", "string")
                    if prop_type == "string":
                        test_input[prop_name] = "test"
                    elif prop_type in ("number", "integer"):
                        test_input[prop_name] = 0
                    elif prop_type == "boolean":
                        test_input[prop_name] = False
                    elif prop_type == "array":
                        test_input[prop_name] = []
                    elif prop_type == "object":
                        test_input[prop_name] = {}
            try:
                output = await self._sandbox.execute_tool(
                    code=tool.code, input_data=test_input, timeout=10
                )
                results.append(
                    ToolValidationResult(tool_name=tool.name, status="pass", output=output)
                )
            except Exception as exc:
                results.append(
                    ToolValidationResult(tool_name=tool.name, status="fail", error=str(exc))
                )
        return ValidateToolsResponse(
            results=results,
            all_passed=all(r.status == "pass" for r in results),
        )

    async def enhance_tool(self, agent_id: str, tool_name: str, instruction: str):
        from ..schemas.builder import EnhanceToolResponse

        agent_def = await self._agent_svc.get_agent(agent_id)
        tool = next((t for t in agent_def.tools if t.name == tool_name), None)
        if tool is None:
            raise ValueError(f"Tool '{tool_name}' not found")

        enhance_prompt = (
            f"Here is a Python tool function:\n\n{tool.code}\n\n"
            f"The user wants: {instruction}\n\n"
            "Rules:\n"
            "- The function must accept a single dict argument called `input_data` and return a dict\n"
            "- Only allowed imports: json, re, datetime, math, requests, bs4, urllib, collections, "
            "itertools, functools, hashlib, base64, html, csv, time, random, string, typing\n"
            "- Do NOT use os, sys, subprocess, socket, or any other restricted module\n\n"
            "Return the improved Python function code. After the code, add a brief explanation on a new line starting with 'EXPLANATION:'"
        )
        response = await self._chat(
            model=agent_def.model,
            messages=[{"role": "user", "content": enhance_prompt}],
        )

        parts = response.split("EXPLANATION:")
        raw_code = parts[0].strip()
        explanation = parts[1].strip() if len(parts) > 1 else "Tool updated successfully."

        cleaned_code = self._clean_code(raw_code)
        validated_code = await self.self_validate_generated_code(
            cleaned_code, agent_def.model
        )

        updated_tool = tool.model_copy(update={"code": validated_code})
        await self._agent_svc.save_tool_code(agent_id, updated_tool)
        updated_tools = [
            updated_tool if t.name == tool_name else t for t in agent_def.tools
        ]
        await self._agent_svc.update_agent(
            agent_id, {"tools": [t.model_dump() for t in updated_tools]}
        )

        return EnhanceToolResponse(tool=updated_tool, explanation=explanation)

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_tool_list(text: str) -> Optional[list[dict[str, Any]]]:
        cleaned = re.sub(r"```(?:json)?\s*", "", text)
        cleaned = re.sub(r"```", "", cleaned).strip()
        try:
            data = json.loads(cleaned)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass
        match = re.search(r"\[[\s\S]*\]", text)
        if match:
            try:
                data = json.loads(match.group())
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                pass
        return None

    @staticmethod
    def _clean_code(text: str) -> str:
        cleaned = re.sub(r"```(?:python)?\s*", "", text)
        cleaned = re.sub(r"```", "", cleaned).strip()
        return cleaned

    @staticmethod
    def _extract_artifacts(text: str) -> Optional[dict[str, Any]]:
        cleaned = re.sub(r"```(?:json)?\s*", "", text)
        cleaned = re.sub(r"```", "", cleaned).strip()
        try:
            data = json.loads(cleaned)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                data = json.loads(match.group())
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                pass
        return None

    async def _apply_artifacts(
        self, agent_id: str, artifacts: dict[str, Any]
    ) -> None:
        updates: dict[str, Any] = {}
        if "system_prompt" in artifacts:
            updates["system_prompt"] = artifacts["system_prompt"]

        agent_def = await self._agent_svc.get_agent(agent_id)

        if "tools" in artifacts and isinstance(artifacts["tools"], list):
            tool_defs: list[ToolDefinition] = []
            for t in artifacts["tools"]:
                try:
                    validated_code = await self.self_validate_generated_code(
                        t.get("code", ""), agent_def.model
                    )
                    td = ToolDefinition(
                        name=t["name"],
                        description=t.get("description", ""),
                        parameters=t.get("parameters", {}),
                        code=validated_code,
                        filename=f"{t['name']}.py",
                    )
                    tool_defs.append(td)
                    await self._agent_svc.save_tool_code(agent_id, td)
                except Exception:
                    logger.warning("Skipping invalid tool definition: %s", t)
            if tool_defs:
                updates["tools"] = [td.model_dump() for td in tool_defs]

        if "flow" in artifacts and isinstance(artifacts["flow"], dict):
            try:
                flow_data = artifacts["flow"]
                nodes = [FlowNode(**n) for n in flow_data.get("nodes", [])]
                edges = [FlowEdge(**e) for e in flow_data.get("edges", [])]
                flow_def = FlowDefinition(
                    nodes=nodes,
                    edges=edges,
                    entry_node=flow_data.get("entry_node", ""),
                )
                await self._agent_svc.save_flow(agent_id, flow_def)
                updates["flow"] = flow_def.model_dump()
            except Exception:
                logger.warning("Skipping invalid flow definition")

        if updates:
            await self._agent_svc.update_agent(agent_id, updates)
