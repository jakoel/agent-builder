"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { RunResult, AgentDefinition } from "@/lib/types";
import RunStatus from "./RunStatus";
import { Clock, ArrowRight, Cpu, ScrollText } from "lucide-react";

interface RunHistoryProps {
  runs: RunResult[];
  agentMap?: Record<string, AgentDefinition>;
  hideAgentColumn?: boolean;
}

function formatDuration(started: string, completed?: string): string {
  if (!completed) return "—";
  const ms = new Date(completed).getTime() - new Date(started).getTime();
  if (ms < 1000) return `${ms}ms`;
  const secs = Math.round(ms / 1000);
  if (secs < 60) return `${secs}s`;
  return `${Math.floor(secs / 60)}m ${secs % 60}s`;
}

function runMode(run: RunResult): "ReAct" | "DAG" | "LLM" {
  if (run.logs.some((l) => l.message.startsWith("ReAct iteration"))) return "ReAct";
  if (run.logs.length > 0 && run.logs.every((l) => l.node_id === "llm")) return "LLM";
  return "DAG";
}

const modeStyle: Record<string, string> = {
  ReAct: "bg-violet-500/10 text-violet-400",
  DAG:   "bg-blue-500/10 text-blue-400",
  LLM:   "bg-slate-700/50 text-slate-400",
};

export default function RunHistory({ runs, agentMap, hideAgentColumn }: RunHistoryProps) {
  const router = useRouter();

  if (runs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <Clock size={32} className="text-slate-700 mb-3" />
        <p className="text-sm text-slate-500">No runs yet.</p>
      </div>
    );
  }

  const sorted = [...runs].sort(
    (a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime()
  );

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-separate border-spacing-y-1.5">
        <thead>
          <tr className="text-left">
            <th className="pb-2 px-4 text-xs font-medium text-slate-500 uppercase tracking-wider">Run ID</th>
            <th className="pb-2 px-4 text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
            {!hideAgentColumn && (
              <th className="pb-2 px-4 text-xs font-medium text-slate-500 uppercase tracking-wider hidden md:table-cell">Agent</th>
            )}
            <th className="pb-2 px-4 text-xs font-medium text-slate-500 uppercase tracking-wider hidden lg:table-cell">Mode</th>
            <th className="pb-2 px-4 text-xs font-medium text-slate-500 uppercase tracking-wider hidden lg:table-cell">Steps</th>
            <th className="pb-2 px-4 text-xs font-medium text-slate-500 uppercase tracking-wider hidden sm:table-cell">Started</th>
            <th className="pb-2 px-4 text-xs font-medium text-slate-500 uppercase tracking-wider">Duration</th>
            <th className="pb-2 w-6" />
          </tr>
        </thead>
        <tbody>
          {sorted.map((run) => {
            const agent = agentMap?.[run.agent_id];
            const mode = runMode(run);
            const steps = run.logs.length;
            const hasError = run.status === "failed" && run.error;

            return (
              <tr
                key={run.run_id}
                onClick={() => router.push(`/runs/${run.run_id}`)}
                className="group bg-slate-900 hover:bg-slate-800/60 border border-slate-800 hover:border-slate-700 rounded-xl cursor-pointer transition-all [&>td:first-child]:rounded-l-xl [&>td:last-child]:rounded-r-xl"
              >
                {/* Run ID */}
                <td className="py-3 px-4">
                  <div className="font-mono text-xs text-slate-400 group-hover:text-slate-200 transition-colors">
                    {run.run_id}
                  </div>
                  {hasError && (
                    <div className="text-xs text-red-400 truncate max-w-[180px] mt-0.5">
                      {run.error}
                    </div>
                  )}
                </td>

                {/* Status */}
                <td className="py-3 px-4 whitespace-nowrap">
                  <RunStatus status={run.status} />
                </td>

                {/* Agent */}
                {!hideAgentColumn && (
                  <td className="py-3 px-4 hidden md:table-cell">
                    {agent ? (
                      <Link
                        href={`/agents/${agent.id}`}
                        onClick={(e) => e.stopPropagation()}
                        className="text-xs text-slate-300 hover:text-violet-400 transition-colors font-medium"
                      >
                        {agent.name}
                      </Link>
                    ) : (
                      <span className="font-mono text-xs text-slate-600">{run.agent_id.slice(0, 8)}…</span>
                    )}
                  </td>
                )}

                {/* Mode */}
                <td className="py-3 px-4 hidden lg:table-cell">
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium ${modeStyle[mode]}`}>
                    <Cpu size={10} />
                    {mode}
                  </span>
                </td>

                {/* Steps */}
                <td className="py-3 px-4 hidden lg:table-cell">
                  <span className="inline-flex items-center gap-1 text-xs text-slate-500">
                    <ScrollText size={11} />
                    {steps}
                  </span>
                </td>

                {/* Started */}
                <td className="py-3 px-4 text-xs text-slate-500 whitespace-nowrap hidden sm:table-cell">
                  {new Date(run.started_at).toLocaleString()}
                </td>

                {/* Duration */}
                <td className="py-3 px-4 text-xs font-mono text-slate-500 whitespace-nowrap">
                  {formatDuration(run.started_at, run.completed_at)}
                </td>

                {/* Arrow */}
                <td className="py-3 pr-4">
                  <ArrowRight size={13} className="text-slate-700 group-hover:text-slate-400 transition-colors" />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
