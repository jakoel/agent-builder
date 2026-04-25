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
import UsageStats from "@/components/runs/UsageStats";
import { Skeleton } from "@/components/ui/Skeleton";
import { startRun, getRuns, updateAgent } from "@/lib/api";
import { RunResult } from "@/lib/types";
import { useEffect } from "react";
import { Play, Save, History, Eye, Zap, Wrench, Calendar } from "lucide-react";
import AgentInputForm from "@/components/runs/AgentInputForm";

type Tab = "overview" | "run" | "history";

export default function AgentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const { agent, loading, error, refetch } = useAgent(id);

  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [editingPrompt, setEditingPrompt] = useState(false);
  const [promptValue, setPromptValue] = useState("");
  const [saving, setSaving] = useState(false);
  const [inputData, setInputData] = useState<Record<string, any>>({});
  const [runId, setRunId] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const { run, liveOutput, connected } = useRun(runId);
  const [runs, setRuns] = useState<RunResult[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  useEffect(() => {
    if (agent) setPromptValue(agent.system_prompt);
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
    } catch {}
    finally { setSaving(false); }
  };

  const handleStartRun = async () => {
    if (!agent) return;
    setStarting(true);
    try {
      const result = await startRun(agent.id, inputData);
      setRunId(result.run_id);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setStarting(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6 max-w-5xl mx-auto space-y-5">
        <div className="space-y-2">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-72" />
        </div>
        <div className="flex gap-1">
          {[1,2,3].map((i) => <Skeleton key={i} className="h-10 w-24 rounded-xl" />)}
        </div>
        <div className="grid grid-cols-3 gap-4">
          {[1,2,3].map((i) => <Skeleton key={i} className="h-20 rounded-2xl" />)}
        </div>
        <Skeleton className="h-40 w-full rounded-2xl" />
      </div>
    );
  }

  if (error || !agent) {
    return (
      <div className="flex items-center justify-center h-64 text-red-400 text-sm">
        {error ?? "Agent not found"}
      </div>
    );
  }

  const tabs: { key: Tab; label: string; icon: React.ReactNode }[] = [
    { key: "overview", label: "Overview", icon: <Eye size={13} /> },
    { key: "run",      label: "Run",      icon: <Zap size={13} /> },
    { key: "history",  label: "History",  icon: <History size={13} /> },
  ];

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-5">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">{agent.name}</h1>
          <p className="text-sm text-slate-500 mt-0.5">{agent.description}</p>
        </div>
        <RunStatus status={agent.status} />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-900 border border-slate-800 rounded-xl p-1 w-fit mb-6">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg transition-all ${
              activeTab === tab.key
                ? "bg-violet-500/15 text-violet-300 shadow-sm"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Overview */}
      {activeTab === "overview" && (
        <div className="space-y-5">
          <div className="grid grid-cols-3 gap-3">
            {[
              { icon: <Wrench size={14} />, label: "Model", value: <span className="font-mono text-xs">{agent.model}</span> },
              { icon: <Wrench size={14} />, label: "Tools", value: `${agent.tools.length}` },
              { icon: <Calendar size={14} />, label: "Created", value: new Date(agent.created_at).toLocaleDateString() },
            ].map(({ icon, label, value }) => (
              <div key={label} className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
                <div className="flex items-center gap-1.5 text-slate-500 text-xs mb-1.5">
                  {icon}
                  <span>{label}</span>
                </div>
                <div className="text-sm font-medium text-slate-200">{value}</div>
              </div>
            ))}
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-slate-300">System Prompt</h3>
              {!editingPrompt ? (
                <button
                  onClick={() => setEditingPrompt(true)}
                  className="text-xs text-violet-400 hover:text-violet-300 transition-colors"
                >
                  Edit
                </button>
              ) : (
                <div className="flex gap-3">
                  <button
                    onClick={() => { setEditingPrompt(false); setPromptValue(agent.system_prompt); }}
                    className="text-xs text-slate-500 hover:text-slate-300"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSavePrompt}
                    disabled={saving}
                    className="flex items-center gap-1 text-xs text-emerald-400 hover:text-emerald-300"
                  >
                    <Save size={11} />
                    {saving ? "Saving…" : "Save"}
                  </button>
                </div>
              )}
            </div>
            <PromptEditor value={promptValue} onChange={setPromptValue} readOnly={!editingPrompt} />
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
            <ToolEditor tools={agent.tools} />
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
            <h3 className="text-sm font-medium text-slate-300 mb-3">Flow</h3>
            <FlowVisualization flow={agent.flow} />
          </div>
        </div>
      )}

      {/* Run */}
      {activeTab === "run" && (
        <div className="space-y-5">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
            <label className="block text-xs font-medium text-slate-400 mb-3 uppercase tracking-wider">
              Input
            </label>
            <AgentInputForm agent={agent} onChange={setInputData} />
          </div>

          <button
            onClick={handleStartRun}
            disabled={starting || (run !== null && run.status === "running")}
            className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-xl shadow-lg shadow-violet-500/20 transition-all"
          >
            <Play size={15} />
            {starting ? "Starting…" : "Run Agent"}
          </button>

          {run && (
            <div className="space-y-4">
              <div className="flex items-center gap-3 flex-wrap">
                <RunStatus status={run.status} />
                {connected && (
                  <span className="text-xs text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded-full">
                    Live
                  </span>
                )}
                {run.current_node && (
                  <span className="text-xs text-slate-500 font-mono bg-slate-800 px-2 py-1 rounded">
                    {run.current_node}
                  </span>
                )}
              </div>

              <UsageStats
                usage={run.usage}
                llmCalls={run.llm_calls}
                totalLatencyMs={run.total_llm_latency_ms}
                provider={run.provider}
              />

              {liveOutput && (
                <div className="bg-slate-900 border border-violet-500/30 rounded-2xl p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-violet-400 opacity-75" />
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-violet-400" />
                    </span>
                    <span className="text-xs font-medium text-violet-300 uppercase tracking-wider">
                      Streaming
                    </span>
                  </div>
                  <pre className="text-sm text-slate-200 whitespace-pre-wrap font-mono leading-relaxed max-h-72 overflow-y-auto">
                    {liveOutput}
                  </pre>
                </div>
              )}

              <RunLogViewer logs={run.logs} />
              {run.output_data && (
                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
                  <h4 className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">Output</h4>
                  <pre className="bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-300 font-mono overflow-auto whitespace-pre-wrap">
                    {JSON.stringify(run.output_data, null, 2)}
                  </pre>
                </div>
              )}
              {run.error && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-sm text-red-400">
                  {run.error}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* History */}
      {activeTab === "history" && (
        <div>
          {historyLoading ? (
            <div className="space-y-2">
              {[1,2,3].map((i) => <Skeleton key={i} className="h-14 w-full rounded-xl" />)}
            </div>
          ) : (
            <RunHistory runs={runs} hideAgentColumn />
          )}
        </div>
      )}
    </div>
  );
}
