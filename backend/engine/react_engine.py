"""ReAct (Reasoning + Acting) loop engine."""

from __future__ import annotations

import json
import re
from typing import Any

from ..schemas.agent import ToolDefinition

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

REACT_SYSTEM = """\
You are an intelligent agent that reasons step by step and uses tools to complete tasks.

INSTRUCTIONS:
- Think carefully before each action.
- Call only ONE tool per step.
- After receiving an Observation, decide whether to call another tool or give the Final Answer.
- The Final Answer should directly address the original task.

STRICT OUTPUT FORMAT — follow exactly:

Thought: <your reasoning>
Action: <tool_name>
Input: <valid JSON object matching the tool's parameter schema>

OR when you are done:

Thought: <your reasoning>
Final Answer: <your complete answer>

Do not add any text outside this format."""

REACT_PROMPT_TEMPLATE = """\
AVAILABLE TOOLS:
================
{tool_descriptions}

TASK:
{task}

{scratchpad}"""


# ---------------------------------------------------------------------------
# Tool schema formatting — this is the "contract" the LLM reads
# ---------------------------------------------------------------------------

def format_tool_schemas(tools: list[ToolDefinition]) -> str:
    """Render tool list as a human+LLM readable schema block."""
    lines: list[str] = []
    for tool in tools:
        lines.append(f"Tool: {tool.name}")
        lines.append(f"  Description: {tool.description}")

        if tool.parameters:
            props = tool.parameters.get("properties", {})
            required = tool.parameters.get("required", [])
            if props:
                lines.append("  Parameters:")
                for param_name, param_def in props.items():
                    req_marker = " (required)" if param_name in required else ""
                    param_type = param_def.get("type", "any")
                    param_desc = param_def.get("description", "")
                    default = param_def.get("default")
                    default_str = f", default={json.dumps(default)}" if default is not None else ""
                    desc_str = f" — {param_desc}" if param_desc else ""
                    lines.append(f"    - {param_name}: {param_type}{req_marker}{default_str}{desc_str}")

        if tool.output_schema:
            props = tool.output_schema.get("properties", {})
            if props:
                lines.append("  Returns:")
                for field_name, field_def in props.items():
                    field_type = field_def.get("type", "any")
                    field_desc = field_def.get("description", "")
                    desc_str = f" — {field_desc}" if field_desc else ""
                    lines.append(f"    - {field_name}: {field_type}{desc_str}")

        lines.append("")  # blank line between tools
    return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# JSON extraction — brace-counting handles nested objects correctly
# ---------------------------------------------------------------------------

def _extract_json_from(text: str, start_char: str = "{") -> str | None:
    """Find and return the first complete JSON object or array in text.

    Uses brace/bracket counting so nested structures are handled correctly,
    unlike a non-greedy regex which stops at the first closing brace.
    """
    openers = {"{": "}", "[": "]"}
    closers = set(openers.values())
    closer = openers.get(start_char)
    if closer is None:
        return None

    start_idx = text.find(start_char)
    if start_idx == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False

    for i in range(start_idx, len(text)):
        ch = text[i]
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == start_char:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return text[start_idx : i + 1]
    return None


def _try_parse_json(text: str) -> dict[str, Any] | None:
    """Attempt to parse JSON from text, trying { and [ starts."""
    for start_char in ("{", "["):
        candidate = _extract_json_from(text, start_char)
        if candidate:
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
    return None


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------

def parse_react_response(text: str) -> tuple[str, Any]:
    """Parse a ReAct-formatted LLM response.

    Returns:
        ("FINAL", answer_string)       — when Final Answer is present
        ("ACTION", (tool_name, args))  — when an Action is present
        ("UNKNOWN", raw_text)          — when neither pattern matches
    """
    # Final Answer — check before Action so "Final Answer" wins if both present
    final_match = re.search(
        r"Final\s+Answer\s*:\s*(.*?)(?:\nThought:|\Z)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if final_match:
        return "FINAL", final_match.group(1).strip()

    # Action line
    action_match = re.search(r"Action\s*:\s*(\w[\w_]*)", text, re.IGNORECASE)
    if not action_match:
        return "UNKNOWN", text

    tool_name = action_match.group(1).strip()

    # Extract JSON after "Input:" using brace counting
    tool_args: dict[str, Any] = {}
    input_marker = re.search(r"Input\s*:", text, re.IGNORECASE)
    if input_marker:
        after_input = text[input_marker.end():]
        parsed = _try_parse_json(after_input)
        if parsed is not None:
            tool_args = parsed if isinstance(parsed, dict) else {"value": parsed}
    else:
        # No "Input:" label — try to find any JSON object in the text as fallback
        parsed = _try_parse_json(text)
        if parsed and isinstance(parsed, dict):
            tool_args = parsed

    return "ACTION", (tool_name, tool_args)


# ---------------------------------------------------------------------------
# Scratchpad helpers
# ---------------------------------------------------------------------------

OBSERVATION_MAX_CHARS = 1500


def build_scratchpad(entries: list[dict[str, str]]) -> str:
    """Format the thought/action/observation history.

    Observations are truncated to OBSERVATION_MAX_CHARS to prevent context
    overflow on local models with limited context windows.
    """
    if not entries:
        return ""
    parts = ["SCRATCHPAD (previous steps):"]
    for entry in entries:
        if entry.get("thought"):
            parts.append(f"Thought: {entry['thought']}")
        if entry.get("action"):
            parts.append(f"Action: {entry['action']}")
        if entry.get("input"):
            parts.append(f"Input: {entry['input']}")
        if entry.get("observation"):
            obs = entry["observation"]
            if len(obs) > OBSERVATION_MAX_CHARS:
                obs = obs[:OBSERVATION_MAX_CHARS] + f"\n... [truncated, {len(entry['observation'])} chars total]"
            parts.append(f"Observation: {obs}")
        parts.append("")
    return "\n".join(parts)
