"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getRun, getAgent } from "@/lib/api";
import { RunResult, AgentDefinition } from "@/lib/types";
import RunLogViewer from "@/components/runs/RunLog";
import RunStatus from "@/components/runs/RunStatus";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  ArrowLeft,
  Bot,
  Clock,
  Cpu,
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

function MetaItem({ icon, label, children }: { icon: React.ReactNode; label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3">
      <span className="w-7 h-7 rounded-lg bg-slate-800 flex items-center justify-center shrink-0 text-slate-500">
        {icon}
      </span>
      <div>
        <p className="text-[10px] text-slate-600 uppercase tracking-wider font-medium">{label}</p>
        <div className="text-sm text-slate-200 mt-0.5">{children}</div>
      </div>
    </div>
  );
}

function Section({
  title,
  collapsible,
  defaultOpen = true,
  children,
}: {
  title: string;
  collapsible?: boolean;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
      <button
        onClick={() => collapsible && setOpen((v) => !v)}
        className={`w-full flex items-center justify-between px-5 py-3.5 text-sm font-medium text-slate-300 ${
          collapsible ? "hover:bg-slate-800/40 transition-colors cursor-pointer" : "cursor-default"
        }`}
      >
        <span>{title}</span>
        {collapsible && (open ? <ChevronUp size={14} /> : <ChevronDown size={14} />)}
      </button>
      {(!collapsible || open) && (
        <div className="border-t border-slate-800 p-5">{children}</div>
      )}
    </div>
  );
}

export default function RunDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [run, setRun] = useState<RunResult | null>(null);
  const [agent, setAgent] = useState<AgentDefinition | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    getRun(id)
      .then(async (r) => {
        setRun(r);
        try { setAgent(await getAgent(r.agent_id)); } catch {}
      })
      .catch(() => setRun(null))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="p-6 max-w-4xl mx-auto space-y-4">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-36 w-full rounded-2xl" />
        <Skeleton className="h-48 w-full rounded-2xl" />
      </div>
    );
  }

  if (!run) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <AlertCircle size={32} className="text-red-400 opacity-60" />
        <p className="text-slate-400">Run not found.</p>
        <Link href="/runs" className="text-sm text-violet-400 hover:text-violet-300">
          ← All runs
        </Link>
      </div>
    );
  }

  const isReact = run.logs.some((l) => l.message.startsWith("ReAct iteration"));
  const reactResult = run.output_data
    ? Object.values(run.output_data).find(
        (v): v is { final_answer: string; iterations: number } =>
          typeof v === "object" && v !== null && "final_answer" in v
      )
    : undefined;
  const iterations = reactResult?.iterations;
  const reactAnswer = reactResult?.final_answer;

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-5">
      {/* Back */}
      <Link
        href={agent ? `/agents/${agent.id}` : "/runs"}
        className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
      >
        <ArrowLeft size={13} />
        {agent ? agent.name : "All runs"}
      </Link>

      {/* Title */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold text-slate-100 font-mono">{run.run_id}</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            {new Date(run.started_at).toLocaleString()}
          </p>
        </div>
        <RunStatus status={run.status} />
      </div>

      {/* Meta */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <MetaItem icon={<Bot size={14} />} label="Agent">
          {agent ? (
            <Link href={`/agents/${agent.id}`} className="text-violet-400 hover:text-violet-300">
              {agent.name}
            </Link>
          ) : (
            <span className="text-slate-500 font-mono text-xs">{run.agent_id.slice(0, 8)}…</span>
          )}
        </MetaItem>
        <MetaItem icon={<Clock size={14} />} label="Duration">
          {formatDuration(run.started_at, run.completed_at)}
        </MetaItem>
        <MetaItem icon={<Cpu size={14} />} label="Mode">
          {isReact ? (
            <span>
              ReAct
              {iterations !== undefined && (
                <span className="text-slate-500 text-xs ml-1">· {iterations} iter</span>
              )}
            </span>
          ) : (
            "DAG"
          )}
        </MetaItem>
        {agent && (
          <MetaItem icon={<Bot size={14} />} label="Model">
            <span className="font-mono text-xs">{agent.model}</span>
          </MetaItem>
        )}
      </div>

      {/* Error */}
      {run.error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-4 flex items-start gap-3">
          <AlertCircle size={15} className="text-red-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-medium text-red-300 mb-1">Run failed</p>
            <p className="text-xs text-red-400 font-mono whitespace-pre-wrap">{run.error}</p>
          </div>
        </div>
      )}

      {/* Input */}
      {run.input_data && Object.keys(run.input_data).length > 0 && (
        <Section title="Input" collapsible defaultOpen={false}>
          <pre className="text-xs text-slate-300 bg-slate-950 border border-slate-800 rounded-xl p-3 overflow-x-auto whitespace-pre-wrap font-mono">
            {JSON.stringify(run.input_data, null, 2)}
          </pre>
        </Section>
      )}

      {/* Output */}
      {run.output_data && (
        <Section title="Output" collapsible defaultOpen>
          <div className="space-y-3">
            {reactAnswer && (
              <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-3">
                <p className="text-xs font-medium text-emerald-400 mb-1.5">Final Answer</p>
                <p className="text-sm text-slate-200 whitespace-pre-wrap">{reactAnswer}</p>
              </div>
            )}
            <pre className="text-xs text-slate-300 bg-slate-950 border border-slate-800 rounded-xl p-3 overflow-x-auto whitespace-pre-wrap font-mono">
              {JSON.stringify(run.output_data, null, 2)}
            </pre>
          </div>
        </Section>
      )}

      {/* Logs */}
      <div className="space-y-2">
        <div className="flex items-center justify-between px-1">
          <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Execution Log
          </h2>
          <span className="text-xs text-slate-600">{run.logs.length} entries</span>
        </div>
        <RunLogViewer logs={run.logs} />
      </div>
    </div>
  );
}
