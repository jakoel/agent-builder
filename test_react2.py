"""
Test 2: Multi-step sales data pipeline via ReAct.

Tools used (in expected order):
  1. csv_parse       — parse raw CSV into records
  2. deduplicate     — remove duplicate rows
  3. calculate_stats — stats on the revenue column
  4. date_calc       — days between first and last sale
  5. format_markdown_report — produce the final report
"""

import json
import sys
import time
from pathlib import Path

import requests

BASE = "http://localhost:8000"

TOOL_DIR = Path(__file__).parent / "backend" / "tool_library"


def _tool(name: str, description: str, parameters: dict, output_schema: dict) -> dict:
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
    "name": "Sales Pipeline Agent",
    "description": "Parses, deduplicates, analyses, and reports on sales CSV data.",
    "system_prompt": "You are a precise data analyst. Use tools to process data step by step.",
    "model": "qwen3-vl:8b",
    "status": "ready",
    "tools": [
        _tool(
            "csv_parse",
            "Parse a CSV string into a list of records (dicts). Returns data, row_count, columns.",
            {
                "type": "object",
                "properties": {
                    "csv_text": {"type": "string", "description": "Raw CSV text to parse"},
                    "delimiter": {"type": "string", "description": "Delimiter character, default ','"},
                },
                "required": ["csv_text"],
            },
            {
                "type": "object",
                "properties": {
                    "data":      {"type": "array",   "description": "List of row dicts"},
                    "row_count": {"type": "integer", "description": "Number of data rows"},
                    "columns":   {"type": "array",   "description": "Column names"},
                },
            },
        ),
        _tool(
            "deduplicate",
            "Remove duplicate records from a list. Returns deduplicated data, original_count, duplicates_removed.",
            {
                "type": "object",
                "properties": {
                    "data":   {"type": "array",  "description": "List of dicts to deduplicate"},
                    "fields": {"type": "array",  "description": "Fields to match on; omit to compare all fields"},
                    "keep":   {"type": "string", "description": "'first' or 'last'"},
                },
                "required": ["data"],
            },
            {
                "type": "object",
                "properties": {
                    "data":               {"type": "array",   "description": "Deduplicated records"},
                    "original_count":     {"type": "integer"},
                    "deduplicated_count": {"type": "integer"},
                    "duplicates_removed": {"type": "integer"},
                },
            },
        ),
        _tool(
            "calculate_stats",
            "Compute min, max, mean, median, std_dev on numeric values. Pass 'values' (list of numbers) OR 'data' (list of dicts) + 'field' (column name).",
            {
                "type": "object",
                "properties": {
                    "values": {"type": "array",  "description": "Flat list of numbers"},
                    "data":   {"type": "array",  "description": "List of dicts when using field"},
                    "field":  {"type": "string", "description": "Numeric field name inside each dict"},
                },
            },
            {
                "type": "object",
                "properties": {
                    "min":     {"type": "number"},
                    "max":     {"type": "number"},
                    "mean":    {"type": "number"},
                    "median":  {"type": "number"},
                    "std_dev": {"type": "number"},
                    "sum":     {"type": "number"},
                    "count":   {"type": "integer"},
                },
            },
        ),
        _tool(
            "date_calc",
            "Date arithmetic. Use operation='diff' with date and date2 to get the number of days between two dates.",
            {
                "type": "object",
                "properties": {
                    "date":      {"type": "string", "description": "First date, e.g. 2026-01-15"},
                    "operation": {"type": "string", "description": "parse | add | subtract | diff"},
                    "date2":     {"type": "string", "description": "Second date for diff"},
                    "days":      {"type": "integer", "description": "Days to add/subtract"},
                },
                "required": ["date"],
            },
            {
                "type": "object",
                "properties": {
                    "result": {"type": "string"},
                    "diff":   {"type": "object", "description": "days, hours, minutes, total_seconds"},
                },
            },
        ),
        _tool(
            "format_markdown_report",
            "Render a structured markdown report. sections is a list of {heading, type, content} dicts. type can be 'text', 'key_value', 'list', or 'table'.",
            {
                "type": "object",
                "properties": {
                    "title":    {"type": "string", "description": "Report title"},
                    "summary":  {"type": "string", "description": "Short summary shown below the title"},
                    "sections": {
                        "type": "array",
                        "description": "List of section dicts: {heading, type, content}",
                    },
                },
                "required": ["title", "sections"],
            },
            {
                "type": "object",
                "properties": {
                    "markdown":      {"type": "string"},
                    "section_count": {"type": "integer"},
                    "char_count":    {"type": "integer"},
                },
            },
        ),
    ],
    "flow": {
        "entry_node": "start",
        "nodes": [
            {"id": "start", "label": "Start",     "type": "start"},
            {"id": "react", "label": "ReAct Loop", "type": "react_agent", "max_iterations": 12},
            {"id": "end",   "label": "End",         "type": "end"},
        ],
        "edges": [
            {"source": "start", "target": "react"},
            {"source": "react", "target": "end"},
        ],
    },
}

# ------------------------------------------------------------------
# Task — deliberately keeps the CSV small so observations stay under
# the 1500-char truncation limit
# ------------------------------------------------------------------

CSV_DATA = """\
product,revenue,sale_date
Widget A,1200,2026-01-15
Widget B,850,2026-01-22
Widget C,2300,2026-02-01
Widget A,1200,2026-01-15
Widget D,975,2026-02-14
Widget B,850,2026-01-22
Widget E,3100,2026-03-05"""

task_input = {
    "task": (
        f"I have the following sales CSV data:\n\n{CSV_DATA}\n\n"
        "Please do all of these steps in order:\n"
        "1. Parse the CSV.\n"
        "2. Deduplicate the records (some products appear twice).\n"
        "3. Calculate statistics (mean, median, min, max, std_dev) on the revenue column "
        "   using the deduplicated data.\n"
        "4. Calculate how many days passed between the first sale (2026-01-15) "
        "   and the last sale (2026-03-05).\n"
        "5. Generate a markdown report with a summary and sections for: "
        "   deduplication results, revenue statistics, and the date range.\n"
        "Use the tools — do not compute anything yourself."
    )
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

print(f"\nStarting run...")
r = requests.post(f"{BASE}/api/runs/", json={"agent_id": agent_id, "input_data": task_input})
r.raise_for_status()
run_id = r.json()["run_id"]
print(f"  Run ID: {run_id}")

# ------------------------------------------------------------------
# Poll
# ------------------------------------------------------------------

print("\nPolling...")
for _ in range(180):
    time.sleep(3)
    r = requests.get(f"{BASE}/api/runs/{run_id}")
    r.raise_for_status()
    run = r.json()
    status = run["status"]
    logs = run.get("logs", [])
    last_log = logs[-1]["message"][:80] if logs else ""
    print(f"  [{status}] {last_log}")
    if status in ("completed", "failed", "cancelled"):
        break
else:
    print("Timeout.")
    sys.exit(1)

# ------------------------------------------------------------------
# Results
# ------------------------------------------------------------------

print(f"\n{'='*60}")
print(f"STATUS: {run['status']}")

if run.get("error"):
    print(f"ERROR:  {run['error']}")

print(f"\n--- LOGS ({len(run.get('logs', []))} entries) ---")
for log in run.get("logs", []):
    print(f"  [{log['node_id']}] {log['message']}")

output = run.get("output_data", {})
react_out = output.get("react", {})

print(f"\n--- FINAL ANSWER ---")
print(react_out.get("final_answer", "(none)"))
print(f"\nCompleted in {react_out.get('iterations', '?')} iterations.")

# Print the markdown report if it was produced
for entry in run.get("logs", []):
    if '"markdown":' in entry["message"]:
        try:
            obs = json.loads(entry["message"].replace("Observation: ", "", 1))
            if "markdown" in obs:
                print(f"\n--- GENERATED REPORT ---\n{obs['markdown']}")
        except Exception:
            pass
