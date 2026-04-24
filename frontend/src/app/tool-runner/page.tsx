"use client";

import { useEffect, useState } from "react";
import { getToolLibrary, runTool } from "@/lib/api";
import {
  Play,
  ChevronDown,
  CheckCircle2,
  XCircle,
  Loader2,
  Info,
} from "lucide-react";

interface ToolMeta {
  name: string;
  display_name: string;
  description: string;
  category: string;
  parameters: {
    type: string;
    properties?: Record<string, ParamDef>;
    required?: string[];
  };
  output_schema?: {
    type: string;
    properties?: Record<string, { type?: string; description?: string }>;
  };
}

interface ParamDef {
  type?: string;
  description?: string;
  default?: any;
  items?: any;
}

// ---------------------------------------------------------------------------
// Dynamic parameter form
// ---------------------------------------------------------------------------

function ParamField({
  name,
  def,
  required,
  value,
  onChange,
}: {
  name: string;
  def: ParamDef;
  required: boolean;
  value: any;
  onChange: (v: any) => void;
}) {
  const type = def.type ?? "string";
  const placeholder = def.description ?? "";
  const label = (
    <label className="block text-xs font-medium text-slate-300 mb-1">
      {name}
      {required && <span className="text-red-400 ml-1">*</span>}
      {def.description && (
        <span className="text-slate-500 font-normal ml-1.5">— {def.description}</span>
      )}
    </label>
  );

  if (type === "boolean") {
    return (
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id={name}
          checked={!!value}
          onChange={(e) => onChange(e.target.checked)}
          className="w-4 h-4 accent-blue-500"
        />
        <label htmlFor={name} className="text-xs font-medium text-slate-300">
          {name}
          {def.description && (
            <span className="text-slate-500 font-normal ml-1.5">— {def.description}</span>
          )}
        </label>
      </div>
    );
  }

  if (type === "integer" || type === "number") {
    return (
      <div>
        {label}
        <input
          type="number"
          value={value ?? ""}
          placeholder={String(def.default ?? placeholder)}
          onChange={(e) =>
            onChange(e.target.value === "" ? undefined : Number(e.target.value))
          }
          className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
        />
      </div>
    );
  }

  if (type === "array" || type === "object") {
    return (
      <div>
        {label}
        <textarea
          rows={4}
          value={
            value === undefined
              ? ""
              : typeof value === "string"
              ? value
              : JSON.stringify(value, null, 2)
          }
          placeholder={`JSON ${type}`}
          onChange={(e) => {
            try {
              onChange(JSON.parse(e.target.value));
            } catch {
              onChange(e.target.value);
            }
          }}
          className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 font-mono resize-y"
        />
      </div>
    );
  }

  // string / fallback
  return (
    <div>
      {label}
      <input
        type="text"
        value={value ?? ""}
        placeholder={String(def.default ?? placeholder)}
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function ToolRunnerPage() {
  const [tools, setTools] = useState<ToolMeta[]>([]);
  const [selected, setSelected] = useState<ToolMeta | null>(null);
  const [fields, setFields] = useState<Record<string, any>>({});
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<{
    status: string;
    output?: any;
    error?: string;
  } | null>(null);

  useEffect(() => {
    getToolLibrary().then((data) => setTools(data as ToolMeta[]));
  }, []);

  // Group by category
  const byCategory = tools.reduce<Record<string, ToolMeta[]>>((acc, t) => {
    (acc[t.category] ??= []).push(t);
    return acc;
  }, {});

  function selectTool(tool: ToolMeta) {
    setSelected(tool);
    setResult(null);
    // Pre-fill defaults
    const defaults: Record<string, any> = {};
    const props = tool.parameters?.properties ?? {};
    for (const [k, v] of Object.entries(props)) {
      if (v.default !== undefined) defaults[k] = v.default;
    }
    setFields(defaults);
  }

  async function handleRun() {
    if (!selected) return;
    setRunning(true);
    setResult(null);
    try {
      const res = await runTool(selected.name, fields);
      setResult(res);
    } catch (err: any) {
      setResult({ status: "error", error: err.message });
    } finally {
      setRunning(false);
    }
  }

  const required = selected?.parameters?.required ?? [];
  const props = selected?.parameters?.properties ?? {};

  return (
    <div className="flex h-full gap-6 p-6">
      {/* Left — tool picker */}
      <aside className="w-72 shrink-0 space-y-4 overflow-y-auto pr-1">
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
          Tool Library
        </h2>
        {Object.entries(byCategory).map(([category, items]) => (
          <div key={category}>
            <p className="text-xs text-slate-500 mb-1.5 font-medium">{category}</p>
            <div className="space-y-1">
              {items.map((t) => (
                <button
                  key={t.name}
                  onClick={() => selectTool(t)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                    selected?.name === t.name
                      ? "bg-blue-600/20 text-blue-300 border border-blue-600/40"
                      : "text-slate-300 hover:bg-slate-800"
                  }`}
                >
                  <span className="font-medium">{t.display_name}</span>
                  <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">
                    {t.description}
                  </p>
                </button>
              ))}
            </div>
          </div>
        ))}
      </aside>

      {/* Right — config + output */}
      <main className="flex-1 min-w-0 space-y-5">
        {!selected ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500">
            <Info size={36} className="mb-3 opacity-40" />
            <p className="text-sm">Select a tool from the left to get started.</p>
          </div>
        ) : (
          <>
            {/* Tool header */}
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h1 className="text-lg font-semibold text-white">
                    {selected.display_name}
                  </h1>
                  <p className="text-sm text-slate-400 mt-0.5">{selected.description}</p>
                  <span className="inline-block mt-2 text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded">
                    {selected.category}
                  </span>
                </div>
              </div>
            </div>

            {/* Parameters */}
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-5 space-y-4">
              <h2 className="text-sm font-semibold text-white">Parameters</h2>
              {Object.keys(props).length === 0 ? (
                <p className="text-sm text-slate-500">This tool takes no parameters.</p>
              ) : (
                Object.entries(props).map(([name, def]) => (
                  <ParamField
                    key={name}
                    name={name}
                    def={def}
                    required={required.includes(name)}
                    value={fields[name]}
                    onChange={(v) => setFields((prev) => ({ ...prev, [name]: v }))}
                  />
                ))
              )}

              <button
                onClick={handleRun}
                disabled={running}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
              >
                {running ? (
                  <Loader2 size={15} className="animate-spin" />
                ) : (
                  <Play size={15} />
                )}
                {running ? "Running…" : "Run Tool"}
              </button>
            </div>

            {/* Output */}
            {result && (
              <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-5 space-y-3">
                <div className="flex items-center gap-2">
                  {result.status === "ok" ? (
                    <CheckCircle2 size={16} className="text-green-400" />
                  ) : (
                    <XCircle size={16} className="text-red-400" />
                  )}
                  <h2 className="text-sm font-semibold text-white">
                    {result.status === "ok" ? "Output" : "Error"}
                  </h2>
                </div>

                {result.status === "error" ? (
                  <pre className="text-sm text-red-400 bg-red-900/20 border border-red-800/30 rounded p-3 overflow-x-auto whitespace-pre-wrap">
                    {result.error}
                  </pre>
                ) : (
                  <>
                    {/* Output schema hint */}
                    {selected.output_schema?.properties && (
                      <div className="flex flex-wrap gap-2 mb-1">
                        {Object.entries(selected.output_schema.properties).map(
                          ([field, def]) => (
                            <span
                              key={field}
                              className="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded"
                              title={def.description}
                            >
                              {field}:{" "}
                              <span className="text-slate-400">{def.type ?? "any"}</span>
                            </span>
                          )
                        )}
                      </div>
                    )}
                    <pre className="text-sm text-slate-200 bg-slate-900 border border-slate-700 rounded p-3 overflow-x-auto whitespace-pre-wrap font-mono">
                      {JSON.stringify(result.output, null, 2)}
                    </pre>
                  </>
                )}
              </div>
            )}

            {/* Output schema reference */}
            {selected.output_schema?.properties && !result && (
              <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl p-4">
                <p className="text-xs font-medium text-slate-500 mb-2">Expected output fields</p>
                <div className="space-y-1">
                  {Object.entries(selected.output_schema.properties).map(
                    ([field, def]) => (
                      <div key={field} className="flex items-baseline gap-2 text-xs">
                        <span className="text-slate-300 font-mono">{field}</span>
                        <span className="text-slate-500">{def.type ?? "any"}</span>
                        {def.description && (
                          <span className="text-slate-600">— {def.description}</span>
                        )}
                      </div>
                    )
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
