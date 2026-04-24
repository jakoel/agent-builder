"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getRun, getAgent } from "@/lib/api";
import { RunResult, AgentDefinition } from "@/lib/types";
import RunLogViewer from "@/components/runs/RunLog";
import RunStatus from "@/components/runs/RunStatus";
import {
  ArrowLeft,
  Bot,
  Clock,
  Hash,
  AlertCircle,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

function formatDuration(started: string, completed?: string): string {
  if (!completed) return "—";
  const ms = new Date(completed).getTime() - new Date(started).getTime();
  if (ms < 1000) return `${ms}ms`;
  const secs = Math.round(ms / 1000);
  if (secs < 60) return `${secs}s`;
  return `${Math.floor(secs / 60)}m ${secs % 60}s`;
}

function MetaRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="text-gray-600 w-4 flex justify-center">{icon}</span>
      <span className="text-gray-500 w-20 shrink-0">{label}</span>
      <span className="text-gray-200">{value}</span>
    </div>
  );
}

export default function RunDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [run, setRun] = useState<RunResult | null>(null);
  const [agent, setAgent] = useState<AgentDefinition | null>(null);
  const [loading, setLoading] = useState(true);
  const [showOutput, setShowOutput] = useState(true);
  const [showInput, setShowInput] = useState(false);

  useEffect(() => {
    if (!id) return;
    getRun(id)
      .then(async (r) => {
        setRun(r);
        try {
          const a = await getAgent(r.agent_id);
          setAgent(a);
        } catch {
          // agent may have been deleted — not critical
        }
      })
      .catch(() => setRun(null))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return <div className="flex items-center justify-center h-64 text-gray-500">Loading…</div>;
  }

  if (!run) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <AlertCircle size={32} className="text-red-400 opacity-60" />
        <p className="text-gray-400">Run not found.</p>
        <Link href="/runs" className="text-sm text-blue-400 hover:text-blue-300">
          ← All runs
        </Link>
      </div>
    );
  }

  const isReact = run.logs.some((l) => l.node_id === "react_agent");
  const iterations = run.output_data?.react_iterations;
  const reactAnswer = run.output_data?.react_answer;

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">

      {/* Header */}
      <div>
        <Link
          href={agent ? `/agents/${agent.id}` : "/runs"}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-300 mb-4 transition-colors"
        >
          <ArrowLeft size={14} />
          {agent ? agent.name : "All runs"}
        </Link>

        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-white font-mono">{run.run_id}</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              {new Date(run.started_at).toLocaleString()}
            </p>
          </div>
          <RunStatus status={run.status} />
        </div>
      </div>

      {/* Metadata */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-3">
        <MetaRow
          icon={<Bot size={14} />}
          label="Agent"
          value={
            agent ? (
              <Link href={`/agents/${agent.id}`} className="text-blue-400 hover:text-blue-300">
                {agent.name}
              </Link>
            ) : (
              <span className="text-gray-500 font-mono text-xs">{run.agent_id}</span>
            )
          }
        />
        <MetaRow
          icon={<Clock size={14} />}
          label="Duration"
          value={formatDuration(run.started_at, run.completed_at)}
        />
        <MetaRow
          icon={<Hash size={14} />}
          label="Mode"
          value={
            isReact ? (
              <span className="flex items-center gap-1.5">
                Autonomous (ReAct)
                {iterations !== undefined && (
                  <span className="text-xs text-gray-500">· {iterations} iteration{iterations !== 1 ? "s" : ""}</span>
                )}
              </span>
            ) : (
              "Structured Flow (DAG)"
            )
          }
        />
        {agent && (
          <MetaRow icon={<Bot size={14} />} label="Model" value={<span className="font-mono text-xs">{agent.model}</span>} />
        )}
        {run.current_node && run.status === "running" && (
          <MetaRow icon={<Hash size={14} />} label="At node" value={<span className="font-mono text-xs">{run.current_node}</span>} />
        )}
      </div>

      {/* Error banner */}
      {run.error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex items-start gap-3">
          <AlertCircle size={16} className="text-red-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-medium text-red-300 mb-1">Run failed</p>
            <p className="text-sm text-red-400 font-mono whitespace-pre-wrap">{run.error}</p>
          </div>
        </div>
      )}

      {/* Input */}
      {run.input_data && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <button
            onClick={() => setShowInput((v) => !v)}
            className="w-full flex items-center justify-between px-5 py-3 text-sm font-medium text-gray-300 hover:bg-gray-800/50 transition-colors"
          >
            <span>Input Data</span>
            {showInput ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
          {showInput && (
            <div className="border-t border-gray-800 p-4">
              <pre className="text-xs text-gray-300 bg-gray-950 border border-gray-800 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap font-mono">
                {JSON.stringify(run.input_data, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Output */}
      {run.output_data && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <button
            onClick={() => setShowOutput((v) => !v)}
            className="w-full flex items-center justify-between px-5 py-3 text-sm font-medium text-gray-300 hover:bg-gray-800/50 transition-colors"
          >
            <span>Output</span>
            {showOutput ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
          {showOutput && (
            <div className="border-t border-gray-800 p-4 space-y-3">
              {/* Surface the final answer at the top for ReAct runs */}
              {reactAnswer && (
                <div className="bg-green-900/20 border border-green-700/30 rounded-lg p-3">
                  <p className="text-xs font-medium text-green-400 mb-1">Final Answer</p>
                  <p className="text-sm text-gray-200 whitespace-pre-wrap">{reactAnswer}</p>
                </div>
              )}
              <pre className="text-xs text-gray-300 bg-gray-950 border border-gray-800 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap font-mono">
                {JSON.stringify(run.output_data, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Logs */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-300">
            Execution Log
            <span className="ml-2 text-xs font-normal text-gray-600">
              {run.logs.length} entries
            </span>
          </h2>
        </div>
        <RunLogViewer logs={run.logs} />
      </div>

    </div>
  );
}
