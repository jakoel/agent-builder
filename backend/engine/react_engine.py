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
You are a precise tool-calling agent. You solve tasks by calling tools and reading their output.

RULES:
1. You MUST call a tool to gather any information — never guess, compute, or assume results.
2. Call exactly ONE tool per turn.
3. The Action line must contain ONLY the exact tool name — no other words.
4. The Input line must be a single valid JSON object on one line.
5. Only write Final Answer after you have called all needed tools and have real Observations.

OUTPUT FORMAT — use exactly one of these two forms per turn:

Form 1 (call a tool):
Thought: <why you are calling this tool>
Action: <exact_tool_name>
Input: {"param": "value"}

Form 2 (finished):
Thought: <summary of what you learned>
Final Answer: <complete answer using only observed data>

EXAMPLE — correct Action line:
  Action: calculate_stats        ← correct
  Action: call calculate_stats   ← WRONG, do not write "call"
  Action: use date_calc          ← WRONG, do not write "use"

Nothing else. No markdown, no extra lines."""

REACT_PROMPT_TEMPLATE = """\
AVAILABLE TOOLS:
================
{tool_descriptions}

TASK:
{task}

{scratchpad}Respond now using the required format."""


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

# Scratchpad rendering tiers:
#   - Most recent SCRATCHPAD_FULL_ENTRIES iterations: shown in full
#   - Next SCRATCHPAD_SUMMARY_ENTRIES iterations: one-line summary only
#   - Older iterations: dropped entirely
# SCRATCHPAD_CHAR_BUDGET is a hard cap applied on top (newest entries kept first).
SCRATCHPAD_FULL_ENTRIES = 2
SCRATCHPAD_SUMMARY_ENTRIES = 6
SCRATCHPAD_CHAR_BUDGET = 6000


def _compress_observation(raw: str) -> str:
    """Replace large list payloads in an observation with a compact summary."""
    try:
        obj = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return raw

    if not isinstance(obj, dict):
        return raw

    compressed = {}
    for key, val in obj.items():
        if isinstance(val, list) and len(val) > 2:
            sample = val[0] if val else {}
            compressed[key] = f"[{len(val)} records — first: {json.dumps(sample)}]"
        else:
            compressed[key] = val

    result = json.dumps(compressed)
    if len(result) > OBSERVATION_MAX_CHARS:
        result = result[:OBSERVATION_MAX_CHARS] + "... [truncated]"
    return result


def _one_line_observation(raw: str) -> str:
    """Reduce an observation to a single short line for the summary tier."""
    try:
        obj = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return raw[:120]

    if not isinstance(obj, dict):
        return raw[:120]

    parts = []
    for k, v in obj.items():
        if isinstance(v, (int, float, bool)):
            parts.append(f"{k}={v}")
        elif isinstance(v, str) and len(v) <= 40:
            parts.append(f"{k}={v!r}")
        elif isinstance(v, list):
            parts.append(f"{k}=[{len(v)} items]")
    result = ", ".join(parts)
    return (result if result else raw)[:120]


def build_scratchpad(entries: list[dict[str, str]]) -> str:
    """Format the thought/action/observation history with tiered compression.

    Recent iterations are shown in full; older ones are collapsed to one-line
    summaries; very old ones are dropped. A character budget enforces a hard
    ceiling, always preserving the newest entries.
    """
    if not entries:
        return ""

    n = len(entries)
    blocks: list[str] = []

    for i, entry in enumerate(entries):
        age = n - 1 - i  # 0 = most recent

        if age >= SCRATCHPAD_FULL_ENTRIES + SCRATCHPAD_SUMMARY_ENTRIES:
            continue  # too old — drop

        lines: list[str] = []
        if age < SCRATCHPAD_FULL_ENTRIES:
            # Full detail — raw observation so the model can use it as tool input
            if entry.get("thought"):
                lines.append(f"Thought: {entry['thought']}")
            if entry.get("action"):
                lines.append(f"Action: {entry['action']}")
            if entry.get("input"):
                lines.append(f"Input: {entry['input']}")
            if entry.get("observation"):
                obs = entry["observation"]
                if len(obs) > OBSERVATION_MAX_CHARS:
                    obs = obs[:OBSERVATION_MAX_CHARS] + "... [truncated]"
                lines.append(f"Observation: {obs}")
        else:
            # Summary line only
            action = entry.get("action", "?")
            obs = _one_line_observation(entry.get("observation", ""))
            lines.append(f"Step {i + 1}: {action} → {obs}")

        blocks.append("\n".join(lines))

    # Apply character budget — keep newest blocks first
    kept: list[str] = []
    total = 0
    for block in reversed(blocks):
        if total + len(block) > SCRATCHPAD_CHAR_BUDGET:
            break
        kept.append(block)
        total += len(block)
    kept.reverse()

    if not kept:
        return ""

    return "SCRATCHPAD (previous steps):\n" + "\n\n".join(kept) + "\n"
