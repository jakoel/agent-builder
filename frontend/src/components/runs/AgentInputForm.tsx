"use client";

import { useState, useEffect } from "react";
import { AgentDefinition } from "@/lib/types";
import { ChevronDown, ChevronUp, Code } from "lucide-react";

interface FieldDef {
  key: string;
  type: string;
  description: string;
  required: boolean;
  default?: any;
  toolName: string;
}

function collectFields(agent: AgentDefinition): FieldDef[] {
  const seen = new Set<string>();
  const fields: FieldDef[] = [];

  // Walk tools in flow order
  const flowOrder: string[] = [];
  if (agent.flow) {
    const edgeMap: Record<string, string> = {};
    for (const e of agent.flow.edges) edgeMap[e.source] = e.target;
    let cur = agent.flow.entry_node;
    while (cur) {
      flowOrder.push(cur);
      cur = edgeMap[cur] ?? "";
    }
  }

  const toolMap = Object.fromEntries(agent.tools.map((t) => [t.name, t]));

  const orderedTools: string[] = [];
  for (const nodeId of flowOrder) {
    const node = agent.flow?.nodes.find((n) => n.id === nodeId);
    if (node?.type === "tool_call" && node.tool_name) {
      orderedTools.push(node.tool_name);
    }
  }
  // Fallback: any tools not in flow
  for (const t of agent.tools) {
    if (!orderedTools.includes(t.name)) orderedTools.push(t.name);
  }

  for (const toolName of orderedTools) {
    const tool = toolMap[toolName];
    if (!tool) continue;
    const props = tool.parameters?.properties ?? {};
    const required: string[] = tool.parameters?.required ?? [];

    for (const [key, schema] of Object.entries<any>(props)) {
      if (seen.has(key)) continue;
      seen.add(key);
      fields.push({
        key,
        type: schema.type ?? "string",
        description: schema.description ?? "",
        required: required.includes(key),
        default: schema.default,
        toolName,
      });
    }
  }

  return fields;
}

function initValues(fields: FieldDef[]): Record<string, string> {
  const vals: Record<string, string> = {};
  for (const f of fields) {
    if (f.default !== undefined) {
      vals[f.key] =
        typeof f.default === "object"
          ? JSON.stringify(f.default)
          : String(f.default);
    } else if (f.type === "boolean") {
      vals[f.key] = "false";
    } else {
      vals[f.key] = "";
    }
  }
  return vals;
}

function buildJson(
  fields: FieldDef[],
  values: Record<string, string>
): Record<string, any> {
  const out: Record<string, any> = {};
  for (const f of fields) {
    const raw = values[f.key];
    if (raw === "" || raw === undefined) continue;
    if (f.type === "integer") {
      out[f.key] = parseInt(raw, 10);
    } else if (f.type === "number") {
      out[f.key] = parseFloat(raw);
    } else if (f.type === "boolean") {
      out[f.key] = raw === "true";
    } else if (f.type === "array") {
      try {
        out[f.key] = JSON.parse(raw);
      } catch {
        out[f.key] = raw.split(",").map((s) => s.trim()).filter(Boolean);
      }
    } else if (f.type === "object") {
      try {
        out[f.key] = JSON.parse(raw);
      } catch {
        out[f.key] = raw;
      }
    } else {
      out[f.key] = raw;
    }
  }
  return out;
}

interface Props {
  agent: AgentDefinition;
  onChange: (json: Record<string, any>) => void;
}

export default function AgentInputForm({ agent, onChange }: Props) {
  const fields = collectFields(agent);
  const [values, setValues] = useState<Record<string, string>>(() =>
    initValues(fields)
  );
  const [showRaw, setShowRaw] = useState(false);

  useEffect(() => {
    onChange(buildJson(fields, values));
  }, [values]); // eslint-disable-line react-hooks/exhaustive-deps

  const set = (key: string, val: string) =>
    setValues((prev) => ({ ...prev, [key]: val }));

  const json = buildJson(fields, values);

  if (fields.length === 0) {
    return (
      <div className="text-sm text-gray-500 italic">
        No input parameters required.
      </div>
    );
  }

  // Group by tool
  const groups: Record<string, FieldDef[]> = {};
  for (const f of fields) {
    (groups[f.toolName] ??= []).push(f);
  }

  return (
    <div className="space-y-5">
      {Object.entries(groups).map(([toolName, toolFields]) => (
        <div key={toolName}>
          <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-2">
            {toolName.replace(/_/g, " ")}
          </p>
          <div className="space-y-3">
            {toolFields.map((f) => (
              <div key={f.key}>
                <label className="flex items-center gap-1.5 text-xs font-medium text-gray-300 mb-1">
                  {f.key}
                  {f.required && (
                    <span className="text-red-400 text-[10px]">required</span>
                  )}
                </label>
                {f.description && (
                  <p className="text-[11px] text-gray-500 mb-1">
                    {f.description}
                  </p>
                )}
                {f.type === "boolean" ? (
                  <select
                    value={values[f.key] ?? "false"}
                    onChange={(e) => set(f.key, e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 rounded-md px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-blue-500"
                  >
                    <option value="true">true</option>
                    <option value="false">false</option>
                  </select>
                ) : f.type === "array" || f.type === "object" ? (
                  <textarea
                    value={values[f.key] ?? ""}
                    onChange={(e) => set(f.key, e.target.value)}
                    rows={2}
                    placeholder={
                      f.type === "array"
                        ? 'item1, item2  or  ["item1","item2"]'
                        : '{"key": "value"}'
                    }
                    className="w-full bg-gray-800 border border-gray-700 rounded-md px-3 py-2 text-sm text-gray-100 font-mono resize-y focus:outline-none focus:border-blue-500"
                  />
                ) : (
                  <input
                    type={f.type === "integer" || f.type === "number" ? "number" : "text"}
                    value={values[f.key] ?? ""}
                    onChange={(e) => set(f.key, e.target.value)}
                    placeholder={f.default !== undefined ? String(f.default) : ""}
                    className="w-full bg-gray-800 border border-gray-700 rounded-md px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-blue-500"
                  />
                )}
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* Raw JSON toggle */}
      <button
        type="button"
        onClick={() => setShowRaw((v) => !v)}
        className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors"
      >
        <Code size={12} />
        {showRaw ? "Hide" : "Show"} raw JSON
        {showRaw ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>
      {showRaw && (
        <pre className="bg-gray-950 border border-gray-800 rounded-lg p-3 text-xs text-gray-400 font-mono overflow-auto">
          {JSON.stringify(json, null, 2)}
        </pre>
      )}
    </div>
  );
}
