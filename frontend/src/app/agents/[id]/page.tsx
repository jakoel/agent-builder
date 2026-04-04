"use client";

import { useCallback, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAgent } from "@/lib/hooks/useAgent";
import { useRun } from "@/lib/hooks/useRun";
import PromptEditor from "@/components/agents/PromptEditor";
import ToolEditor from "@/components/agents/ToolEditor";
import FlowVisualization from "@/components/flow/FlowVisualization";
import RunStatus from "@/components/runs/RunStatus";
import RunLogViewer from "@/components/runs/RunLog";
import RunHistory from "@/components/runs/RunHistory";
import { startRun, getRuns, updateAgent } from "@/lib/api";
import { RunResult } from "@/lib/types";
import { useEffect } from "react";
import { Play, Save, History, Eye, Zap } from "lucide-react";

type Tab = "overview" | "run" | "history";

export default function AgentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const { agent, loading, error, refetch } = useAgent(id);

  const [activeTab, setActiveTab] = useState<Tab>("overview");

  // Overview state
  const [editingPrompt, setEditingPrompt] = useState(false);
  const [promptValue, setPromptValue] = useState("");
  const [saving, setSaving] = useState(false);

  // Run state
  const [inputJson, setInputJson] = useState("{}");
  const [runId, setRunId] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const { run, connected } = useRun(runId);

  // History state
  const [runs, setRuns] = useState<RunResult[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  useEffect(() => {
    if (agent) {
      setPromptValue(agent.system_prompt);
    }
  }, [agent]);

  useEffect(() => {
    if (activeTab === "history" && id) {
      setHistoryLoading(true);
      getRuns(id)
        .then(setRuns)
        .catch(() => {})
        .finally(() => setHistoryLoading(false));
    }
  }, [activeTab, id]);

  const handleSavePrompt = async () => {
    if (!agent) return;
    setSaving(true);
    try {
      await updateAgent(agent.id, { system_prompt: promptValue });
      setEditingPrompt(false);
      refetch();
    } catch {
      // ignore
    } finally {
      setSaving(false);
    }
  };

  const handleStartRun = async () => {
    if (!agent) return;
    setStarting(true);
    try {
      const parsed = JSON.parse(inputJson);
      const result = await startRun(agent.id, parsed);
      setRunId(result.run_id);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setStarting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        Loading...
      </div>
    );
  }

  if (error || !agent) {
    return (
      <div className="flex items-center justify-center h-64 text-red-400">
        {error ?? "Agent not found"}
      </div>
    );
  }

  const tabs: { key: Tab; label: string; icon: React.ReactNode }[] = [
    { key: "overview", label: "Overview", icon: <Eye size={14} /> },
    { key: "run", label: "Run", icon: <Zap size={14} /> },
    { key: "history", label: "History", icon: <History size={14} /> },
  ];

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <div className="flex-1">
          <h1 className="text-xl font-bold text-white">{agent.name}</h1>
          <p className="text-sm text-gray-400 mt-0.5">
            {agent.description}
          </p>
        </div>
        <RunStatus status={agent.status} />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-800 mb-6">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? "text-blue-400 border-b-2 border-blue-400"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
              <span className="text-gray-500">Model</span>
              <p className="font-mono text-gray-200 mt-1">{agent.model}</p>
            </div>
            <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
              <span className="text-gray-500">Tools</span>
              <p className="text-gray-200 mt-1">{agent.tools.length}</p>
            </div>
            <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
              <span className="text-gray-500">Created</span>
              <p className="text-gray-200 mt-1">
                {new Date(agent.created_at).toLocaleDateString()}
              </p>
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-gray-300">
                System Prompt
              </h3>
              {!editingPrompt ? (
                <button
                  onClick={() => setEditingPrompt(true)}
                  className="text-xs text-blue-400 hover:text-blue-300"
                >
                  Edit
                </button>
              ) : (
                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      setEditingPrompt(false);
                      setPromptValue(agent.system_prompt);
                    }}
                    className="text-xs text-gray-400 hover:text-gray-300"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSavePrompt}
                    disabled={saving}
                    className="flex items-center gap-1 text-xs text-green-400 hover:text-green-300"
                  >
                    <Save size={12} />
                    {saving ? "Saving..." : "Save"}
                  </button>
                </div>
              )}
            </div>
            <PromptEditor
              value={promptValue}
              onChange={setPromptValue}
              readOnly={!editingPrompt}
            />
          </div>

          <ToolEditor tools={agent.tools} />

          <div>
            <h3 className="text-sm font-medium text-gray-300 mb-2">
              Flow
            </h3>
            <FlowVisualization flow={agent.flow} />
          </div>
        </div>
      )}

      {/* Run Tab */}
      {activeTab === "run" && (
        <div className="space-y-6">
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">
              Input Data (JSON)
            </label>
            <textarea
              value={inputJson}
              onChange={(e) => setInputJson(e.target.value)}
              rows={6}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-sm text-gray-100 font-mono resize-y focus:outline-none focus:border-blue-500"
              placeholder='{"key": "value"}'
            />
          </div>
          <button
            onClick={handleStartRun}
            disabled={starting || (run !== null && run.status === "running")}
            className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <Play size={16} />
            {starting ? "Starting..." : "Run Agent"}
          </button>

          {run && (
            <div className="space-y-4">
              <div className="flex items-center gap-4">
                <RunStatus status={run.status} />
                {connected && (
                  <span className="text-xs text-green-400">
                    Connected (SSE)
                  </span>
                )}
                {run.current_node && (
                  <span className="text-xs text-gray-400">
                    Node: {run.current_node}
                  </span>
                )}
              </div>
              <RunLogViewer logs={run.logs} />
              {run.output_data && (
                <div>
                  <h4 className="text-sm font-medium text-gray-300 mb-2">
                    Output
                  </h4>
                  <pre className="bg-gray-950 border border-gray-800 rounded-lg p-4 text-xs text-gray-300 font-mono overflow-auto">
                    {JSON.stringify(run.output_data, null, 2)}
                  </pre>
                </div>
              )}
              {run.error && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 text-sm text-red-400">
                  {run.error}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* History Tab */}
      {activeTab === "history" && (
        <div>
          {historyLoading ? (
            <div className="text-center py-8 text-gray-500">Loading...</div>
          ) : (
            <RunHistory runs={runs} />
          )}
        </div>
      )}
    </div>
  );
}
