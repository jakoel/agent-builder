"""
Test 3: Student grade analysis pipeline.

Tools (in expected order):
  1. csv_parse       — parse 12 rows (2 are duplicates)
  2. deduplicate     — produce 10 unique student records
  3. calculate_stats — stats on ALL scores
  4. json_transform  — filter students who passed (score >= 60)
  5. calculate_stats — stats on passing students' scores only
  6. compare_values  — compare all-student stats dict vs passer stats dict
  7. format_markdown — final report

Validation: every numeric result is checked against values computed here
in pure Python before the agent ever runs.
"""

import json
import math
import sys
import time
from pathlib import Path

import requests

BASE = "http://localhost:8000"
TOOL_DIR = Path(__file__).parent / "backend" / "tool_library"

# ------------------------------------------------------------------
# Pre-compute expected values  (ground truth for validation)
# ------------------------------------------------------------------

ALL_SCORES = [92, 78, 85, 45, 91, 88, 72, 55, 95, 63]   # after dedup
PASS_SCORES = [s for s in ALL_SCORES if s >= 60]         # [92,78,85,91,88,72,95,63]


def _stats(values):
    n = len(values)
    s = sorted(values)
    mean = sum(s) / n
    # linear-interpolation percentile (matches calculate_stats impl)
    rank = 0.5 * (n - 1)
    lo, hi = int(math.floor(rank)), int(math.ceil(rank))
    median = s[lo] + (rank - lo) * (s[hi] - s[lo])
    variance = sum((x - mean) ** 2 for x in s) / n
    return {
        "count":   n,
        "sum":     float(sum(s)),
        "mean":    mean,
        "median":  median,
        "min":     float(min(s)),
        "max":     float(max(s)),
        "std_dev": math.sqrt(variance),
    }


EXPECTED_ALL   = _stats(ALL_SCORES)
EXPECTED_PASS  = _stats(PASS_SCORES)

print("=== PRE-COMPUTED EXPECTED VALUES ===")
print(f"All students  ({EXPECTED_ALL['count']} records): "
      f"mean={EXPECTED_ALL['mean']:.4f}, median={EXPECTED_ALL['median']:.1f}, "
      f"std_dev={EXPECTED_ALL['std_dev']:.4f}")
print(f"Passers only  ({EXPECTED_PASS['count']} records): "
      f"mean={EXPECTED_PASS['mean']:.4f}, median={EXPECTED_PASS['median']:.1f}, "
      f"std_dev={EXPECTED_PASS['std_dev']:.4f}")
print()

# ------------------------------------------------------------------
# CSV data (12 rows, 2 intentional duplicates)
# ------------------------------------------------------------------

CSV_DATA = """\
student_id,name,subject,score,exam_date
S001,Alice,Math,92,2026-03-01
S002,Bob,Math,78,2026-03-01
S003,Carol,Math,85,2026-03-01
S004,Dave,Math,45,2026-03-01
S005,Eve,Math,91,2026-03-01
S001,Alice,Math,92,2026-03-01
S006,Frank,Science,88,2026-03-05
S007,Grace,Science,72,2026-03-05
S008,Henry,Science,55,2026-03-05
S009,Ivy,Science,95,2026-03-05
S010,Jack,Science,63,2026-03-05
S006,Frank,Science,88,2026-03-05"""

# ------------------------------------------------------------------
# Tool helpers
# ------------------------------------------------------------------

def _tool(name, description, parameters, output_schema):
    return {
        "name": name,
        "description": description,
        "parameters": parameters,
        "output_schema": output_schema,
        "code": (TOOL_DIR / f"{name}.py").read_text(),
        "filename": f"{name}.py",
    }


# ------------------------------------------------------------------
# Agent definition
# ------------------------------------------------------------------

agent_payload = {
    "id": "",
    "name": "Student Grade Analyst",
    "description": "Analyses student grade data: dedup, stats, filtering, comparison, report.",
    "system_prompt": "You are a precise data analyst. Always use tools for every calculation.",
    "model": "qwen3-vl:8b",
    "status": "ready",
    "tools": [
        _tool("csv_parse",
              "Parse a CSV string into a list of row dicts. Returns data (list), row_count, columns.",
              {"type": "object",
               "properties": {"csv_text": {"type": "string"}},
               "required": ["csv_text"]},
              {"type": "object",
               "properties": {"data": {"type": "array"}, "row_count": {"type": "integer"},
                              "columns": {"type": "array"}}}),

        _tool("deduplicate",
              "Remove duplicate records from a list. Compares all fields when 'fields' is omitted. "
              "Returns data, original_count, deduplicated_count, duplicates_removed.",
              {"type": "object",
               "properties": {"data":   {"type": "array", "description": "List of row dicts"},
                              "fields": {"type": "array", "description": "Fields to match on; omit to compare all fields"},
                              "keep":   {"type": "string", "description": "'first' or 'last'"}},
               "required": ["data"]},
              {"type": "object",
               "properties": {"data": {"type": "array"}, "original_count": {"type": "integer"},
                              "deduplicated_count": {"type": "integer"},
                              "duplicates_removed": {"type": "integer"}}}),

        _tool("calculate_stats",
              "Compute min, max, mean, median, std_dev on numeric values. "
              "Use 'data' (list of dicts) + 'field' (column name) to compute stats on one column, "
              "or 'values' (flat list of numbers) for direct computation. "
              "The tool handles string-valued numbers from CSV automatically.",
              {"type": "object",
               "properties": {"values": {"type": "array",  "description": "Flat list of numbers"},
                              "data":   {"type": "array",  "description": "List of row dicts"},
                              "field":  {"type": "string", "description": "Numeric column name"}}},
              {"type": "object",
               "properties": {"min": {"type": "number"}, "max": {"type": "number"},
                              "mean": {"type": "number"}, "median": {"type": "number"},
                              "std_dev": {"type": "number"}, "sum": {"type": "number"},
                              "count": {"type": "integer"}}}),

        _tool("json_transform",
              "Filter, sort, or select fields from a list of dicts. "
              "Use filter_field + filter_op + filter_value to subset rows. "
              "filter_op options: eq, ne, gt, lt, gte, lte, contains, in. "
              "Numeric filter_value is compared numerically even when field values are CSV strings.",
              {"type": "object",
               "properties": {
                   "data":          {"type": "array",  "description": "Input list of dicts"},
                   "filter_field":  {"type": "string", "description": "Field name to filter on"},
                   "filter_op":     {"type": "string", "description": "Comparison operator"},
                   "filter_value":  {"description":    "Value to compare against"},
                   "sort_by":       {"type": "string", "description": "Field to sort by"},
                   "sort_desc":     {"type": "boolean"},
                   "select_fields": {"type": "array",  "description": "Fields to keep"},
               },
               "required": ["data"]},
              {"type": "object",
               "properties": {"data": {"type": "array"}, "count": {"type": "integer"}}}),

        _tool("compare_values",
              "Compare two dicts and report which keys changed, were added, or removed. "
              "Pass old and new as plain dicts with matching keys.",
              {"type": "object",
               "properties": {"old": {"type": "object", "description": "Previous dict"},
                              "new": {"type": "object", "description": "Current dict"}},
               "required": ["old", "new"]},
              {"type": "object",
               "properties": {"summary": {"type": "string"}, "modified": {"type": "array"},
                              "added": {"type": "array"}, "removed": {"type": "array"},
                              "unchanged_count": {"type": "integer"}}}),

        _tool("format_markdown_report",
              "Render a structured markdown report. "
              "sections is a list of {heading, type, content} dicts. "
              "type can be 'text', 'key_value' (content=dict), 'list' (content=list), or 'table' (content=list of dicts).",
              {"type": "object",
               "properties": {
                   "title":    {"type": "string"},
                   "summary":  {"type": "string"},
                   "sections": {"type": "array",
                                "description": "List of {heading, type, content} dicts"},
               },
               "required": ["title", "sections"]},
              {"type": "object",
               "properties": {"markdown": {"type": "string"}, "char_count": {"type": "integer"},
                              "section_count": {"type": "integer"}}}),
    ],
    "flow": {
        "entry_node": "start",
        "nodes": [
            {"id": "start", "label": "Start",     "type": "start"},
            {"id": "react", "label": "ReAct Loop", "type": "react_agent", "max_iterations": 18},
            {"id": "end",   "label": "End",         "type": "end"},
        ],
        "edges": [
            {"source": "start", "target": "react"},
            {"source": "react", "target": "end"},
        ],
    },
}

# ------------------------------------------------------------------
# Task
# ------------------------------------------------------------------

task_input = {
    "task": (
        f"Here is exam data for 12 student records (some students appear twice due to a logging error):\n\n"
        f"{CSV_DATA}\n\n"
        "Complete ALL of these steps using only the available tools:\n"
        "1. csv_parse — parse the CSV.\n"
        "2. deduplicate — remove duplicate rows (compare all fields).\n"
        "3. calculate_stats on the 'score' column for ALL deduplicated students.\n"
        "4. json_transform — filter to keep only students who passed (score >= 60).\n"
        "5. calculate_stats on the passing students' scores only.\n"
        "6. compare_values — compare {mean, min, max} of all-student stats vs passer stats.\n"
        "7. format_markdown_report — include Deduplication, Score Statistics, Comparison, "
        "   and Failing Students sections.\n"
        "Do not skip any step. Do not guess any number — every value must come from a tool observation."
    ),
}

# ------------------------------------------------------------------
# Create agent
# ------------------------------------------------------------------

print("Creating agent...")
r = requests.post(f"{BASE}/api/agents/", json=agent_payload)
r.raise_for_status()
agent_id = r.json()["id"]
print(f"  Agent ID: {agent_id}")

# ------------------------------------------------------------------
# Start run
# ------------------------------------------------------------------

print("Starting run...")
r = requests.post(f"{BASE}/api/runs/", json={"agent_id": agent_id, "input_data": task_input})
r.raise_for_status()
run_id = r.json()["run_id"]
print(f"  Run ID: {run_id}\n")

# ------------------------------------------------------------------
# Poll
# ------------------------------------------------------------------

print("Polling...")
for _ in range(300):
    time.sleep(4)
    r = requests.get(f"{BASE}/api/runs/{run_id}")
    r.raise_for_status()
    run = r.json()
    status = run["status"]
    logs = run.get("logs", [])
    last = logs[-1]["message"][:80] if logs else ""
    print(f"  [{status}] {last}")
    if status in ("completed", "failed", "cancelled"):
        break
else:
    print("Timeout.")
    sys.exit(1)

# ------------------------------------------------------------------
# Print logs
# ------------------------------------------------------------------

print(f"\n{'='*60}")
print(f"STATUS: {run['status']}")
if run.get("error"):
    print(f"ERROR:  {run['error']}")

print(f"\n--- LOGS ({len(run.get('logs', []))} entries) ---")
for log in run.get("logs", []):
    print(f"  [{log['node_id']}] {log['message']}")

react_out = run.get("output_data", {}).get("react", {})
print(f"\nCompleted in {react_out.get('iterations', '?')} iterations.")

# ------------------------------------------------------------------
# Extract tool observations from logs for validation
# ------------------------------------------------------------------

observations = {}
tool_sequence = []
for log in run.get("logs", []):
    msg = log["message"]
    if msg.startswith("Calling tool:"):
        tool_name = msg.split("Calling tool:")[1].split("args=")[0].strip()
        tool_sequence.append(tool_name)
    if msg.startswith("Observation:"):
        raw = msg[len("Observation:"):].strip()
        try:
            obs = json.loads(raw)
            # associate with the most recently called tool
            if tool_sequence:
                observations[tool_sequence[-1]] = obs
        except Exception:
            pass

print(f"\n--- TOOL CALL SEQUENCE ---")
print("  " + " → ".join(tool_sequence))

# ------------------------------------------------------------------
# Validate
# ------------------------------------------------------------------

TOLERANCE = 0.01   # allow rounding differences
errors = []
warnings = []


def _close(a, b, name):
    if abs(a - b) > TOLERANCE:
        errors.append(f"FAIL {name}: expected {b:.4f}, got {a:.4f}")
    else:
        print(f"  ✓  {name}: {a:.4f} (expected {b:.4f})")


def _eq(a, b, name):
    if a != b:
        errors.append(f"FAIL {name}: expected {b!r}, got {a!r}")
    else:
        print(f"  ✓  {name}: {a!r}")


print(f"\n--- VALIDATION ---")

# 1. csv_parse
cp = observations.get("csv_parse", {})
_eq(cp.get("row_count"), 12, "csv_parse.row_count")

# 2. deduplicate
dd = observations.get("deduplicate", {})
_eq(dd.get("original_count"),     12, "deduplicate.original_count")
_eq(dd.get("deduplicated_count"), 10, "deduplicate.deduplicated_count")
_eq(dd.get("duplicates_removed"),  2, "deduplicate.duplicates_removed")

# 3. calculate_stats (all)  — first call
stats_all_obs = None
stats_pass_obs = None
calc_calls = [o for t, o in zip(tool_sequence, [observations.get(t) for t in tool_sequence]) if t == "calculate_stats"]
# tool_sequence may have two "calculate_stats" entries; observations dict only keeps the last.
# Reconstruct per-call observations from log order.
per_call: list[dict] = []
pending_tool = None
for log in run.get("logs", []):
    msg = log["message"]
    if msg.startswith("Calling tool: calculate_stats"):
        pending_tool = "calculate_stats"
    elif msg.startswith("Observation:") and pending_tool == "calculate_stats":
        raw = msg[len("Observation:"):].strip()
        try:
            per_call.append(json.loads(raw))
        except Exception:
            pass
        pending_tool = None

if len(per_call) >= 1:
    stats_all_obs = per_call[0]
    print("\n  [All students stats]")
    _close(stats_all_obs.get("mean",    0), EXPECTED_ALL["mean"],    "all.mean")
    _close(stats_all_obs.get("median",  0), EXPECTED_ALL["median"],  "all.median")
    _close(stats_all_obs.get("min",     0), EXPECTED_ALL["min"],     "all.min")
    _close(stats_all_obs.get("max",     0), EXPECTED_ALL["max"],     "all.max")
    _close(stats_all_obs.get("std_dev", 0), EXPECTED_ALL["std_dev"], "all.std_dev")
    _eq(stats_all_obs.get("count"),        EXPECTED_ALL["count"],    "all.count")

if len(per_call) >= 2:
    stats_pass_obs = per_call[1]
    print("\n  [Passers stats]")
    _close(stats_pass_obs.get("mean",    0), EXPECTED_PASS["mean"],    "passers.mean")
    _close(stats_pass_obs.get("median",  0), EXPECTED_PASS["median"],  "passers.median")
    _close(stats_pass_obs.get("min",     0), EXPECTED_PASS["min"],     "passers.min")
    _close(stats_pass_obs.get("max",     0), EXPECTED_PASS["max"],     "passers.max")
    _close(stats_pass_obs.get("std_dev", 0), EXPECTED_PASS["std_dev"], "passers.std_dev")
    _eq(stats_pass_obs.get("count"),         EXPECTED_PASS["count"],   "passers.count")

# 4. json_transform (filter passers)
jt = observations.get("json_transform", {})
_eq(jt.get("count"), len(PASS_SCORES), "json_transform.count (passers)")

# 5. compare_values
cv = observations.get("compare_values", {})
if cv:
    print(f"\n  [compare_values] summary: {cv.get('summary', '(missing)')}")
    unchanged = cv.get("unchanged_count", -1)
    modified  = cv.get("modified", [])
    if unchanged == 1:
        print(f"  ✓  compare_values.unchanged_count: 1 (max is the same)")
    else:
        errors.append(f"FAIL compare_values.unchanged_count: expected 1, got {unchanged}")
    if len(modified) == 2:
        print(f"  ✓  compare_values.modified: 2 keys changed (mean, min)")
    else:
        errors.append(f"FAIL compare_values.modified count: expected 2, got {len(modified)}")
else:
    warnings.append("compare_values observation not found in logs")

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------

print(f"\n{'='*60}")
if errors:
    print(f"FAILED — {len(errors)} error(s):")
    for e in errors: print(f"  {e}")
else:
    print("ALL CHECKS PASSED")
if warnings:
    for w in warnings: print(f"  WARNING: {w}")
