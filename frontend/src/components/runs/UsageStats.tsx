"use client";

import { TokenUsage } from "@/lib/types";
import { Coins, Hash, Zap, ArrowUp, ArrowDown } from "lucide-react";

interface UsageStatsProps {
  usage?: TokenUsage;
  llmCalls?: number;
  totalLatencyMs?: number;
  provider?: string;
}

function formatTokens(n: number): string {
  if (n < 1000) return `${n}`;
  if (n < 1_000_000) return `${(n / 1000).toFixed(1)}k`;
  return `${(n / 1_000_000).toFixed(2)}M`;
}

function formatCost(c: number): string {
  if (c === 0) return "$0";
  if (c < 0.01) return `$${(c * 100).toFixed(2)}¢`;
  return `$${c.toFixed(c < 1 ? 4 : 2)}`;
}

function formatLatency(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export default function UsageStats({ usage, llmCalls, totalLatencyMs, provider }: UsageStatsProps) {
  if (!usage || (usage.total_tokens === 0 && (llmCalls ?? 0) === 0)) {
    return null;
  }

  const stats = [
    {
      icon: <ArrowUp size={12} />,
      label: "Input",
      value: formatTokens(usage.prompt_tokens),
      color: "text-sky-400",
    },
    {
      icon: <ArrowDown size={12} />,
      label: "Output",
      value: formatTokens(usage.completion_tokens),
      color: "text-emerald-400",
    },
    {
      icon: <Coins size={12} />,
      label: "Cost",
      value: formatCost(usage.cost_usd),
      color: "text-amber-400",
    },
    {
      icon: <Hash size={12} />,
      label: "Calls",
      value: `${llmCalls ?? 0}`,
      color: "text-violet-400",
    },
    {
      icon: <Zap size={12} />,
      label: "LLM time",
      value: formatLatency(totalLatencyMs ?? 0),
      color: "text-pink-400",
    },
  ];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-medium text-slate-400 uppercase tracking-wider">Usage</h3>
        {provider && (
          <span className="text-[10px] font-medium text-slate-500 bg-slate-800 px-2 py-0.5 rounded-full uppercase tracking-wider">
            {provider}
          </span>
        )}
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {stats.map(({ icon, label, value, color }) => (
          <div key={label} className="bg-slate-950/50 border border-slate-800 rounded-xl p-2.5">
            <div className={`flex items-center gap-1 ${color} mb-1`}>
              {icon}
              <span className="text-[10px] font-medium uppercase tracking-wider opacity-80">{label}</span>
            </div>
            <div className="text-sm font-mono font-semibold text-slate-200">{value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
