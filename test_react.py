"""Test a ReAct agent end-to-end via the HTTP API."""

import json
import sys
import time

import requests

BASE = "http://localhost:8000"

# ------------------------------------------------------------------
# Tool code (inlined from tool_library/)
# ------------------------------------------------------------------

def _read_tool(filename: str) -> str:
    from pathlib import Path
    return (Path(__file__).parent / "backend" / "tool_library" / filename).read_text()


# ------------------------------------------------------------------
# Agent definition
# ------------------------------------------------------------------

agent_payload = {
    "id": "",  # server will assign
    "name": "ReAct Stats & Date Agent",
    "description": "Uses ReAct loop to answer questions using calculate_stats and date_calc tools.",
    "system_prompt": "You are a helpful data analysis assistant.",
    "model": "qwen3-vl:8b",
    "status": "ready",
    "tools": [
        {
            "name": "calculate_stats",
            "description": "Compute min, max, mean, median, std_dev on a list of numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "values": {"type": "array", "items": {"type": "number"}, "description": "List of numbers to analyse"}
                },
                "required": ["values"]
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "min": {"type": "number"},
                    "max": {"type": "number"},
                    "mean": {"type": "number"},
                    "median": {"type": "number"},
                    "std_dev": {"type": "number"},
                    "sum": {"type": "number"},
                    "count": {"type": "integer"}
                }
            },
            "code": _read_tool("calculate_stats.py"),
            "filename": "calculate_stats.py",
        },
        {
            "name": "date_calc",
            "description": "Add or subtract days from a date, or compute the difference between two dates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date":      {"type": "string", "description": "Date string, e.g. 2026-04-25"},
                    "operation": {"type": "string", "description": "parse | add | subtract | diff"},
                    "days":      {"type": "integer", "description": "Days to add or subtract"},
                    "date2":     {"type": "string", "description": "Second date for diff operation"}
                },
                "required": ["date"]
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "result": {"type": "string"},
                    "iso":    {"type": "string"}
                }
            },
            "code": _read_tool("date_calc.py"),
            "filename": "date_calc.py",
        },
    ],
    "flow": {
        "entry_node": "start",
        "nodes": [
            {"id": "start",  "label": "Start",      "type": "start"},
            {"id": "react",  "label": "ReAct Loop",  "type": "react_agent", "max_iterations": 10},
            {"id": "end",    "label": "End",          "type": "end"},
        ],
        "edges": [
            {"source": "start", "target": "react"},
            {"source": "react", "target": "end"},
        ],
    },
}

# ------------------------------------------------------------------
# Create agent
# ------------------------------------------------------------------

print("Creating agent...")
resp = requests.post(f"{BASE}/api/agents/", json=agent_payload)
resp.raise_for_status()
agent = resp.json()
agent_id = agent["id"]
print(f"  Agent ID: {agent_id}")

# ------------------------------------------------------------------
# Start run
# ------------------------------------------------------------------

task = {
    "task": (
        "I have the numbers [4, 8, 15, 16, 23, 42]. "
        "First, calculate their statistics (mean, median, std_dev). "
        "Then tell me what date it will be 100 days from today (2026-04-25). "
        "Summarise both results."
    )
}

print(f"\nStarting run with task:\n  {task['task']}\n")
resp = requests.post(f"{BASE}/api/runs/", json={"agent_id": agent_id, "input_data": task})
resp.raise_for_status()
run = resp.json()
run_id = run["run_id"]
print(f"  Run ID: {run_id}")

# ------------------------------------------------------------------
# Poll until done
# ------------------------------------------------------------------

print("\nPolling...")
for _ in range(120):
    time.sleep(2)
    resp = requests.get(f"{BASE}/api/runs/{run_id}")
    resp.raise_for_status()
    run = resp.json()
    status = run["status"]
    print(f"  status={status}", end="", flush=True)
    if status in ("completed", "failed", "cancelled"):
        print()
        break
    print()
else:
    print("\nTimeout waiting for run.")
    sys.exit(1)

# ------------------------------------------------------------------
# Results
# ------------------------------------------------------------------

print(f"\n{'='*60}")
print(f"STATUS: {run['status']}")

if run.get("error"):
    print(f"ERROR: {run['error']}")

print(f"\n--- LOGS ({len(run.get('logs', []))} entries) ---")
for log in run.get("logs", []):
    print(f"  [{log['node_id']}] {log['message']}")

print(f"\n--- OUTPUT ---")
print(json.dumps(run.get("output_data"), indent=2))
