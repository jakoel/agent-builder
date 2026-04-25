"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AgentDefinition } from "@/lib/types";
import { getAgents, deleteAgent } from "@/lib/api";
import AgentCard from "@/components/agents/AgentCard";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { PlusCircle, Bot } from "lucide-react";
import Link from "next/link";

export default function DashboardPage() {
  const router = useRouter();
  const [agents, setAgents] = useState<AgentDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadAgents = async () => {
    try {
      const data = await getAgents();
      setAgents(data);
    } catch (err: any) {
      setError(err.message ?? "Failed to load agents");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadAgents(); }, []);

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this agent? This cannot be undone.")) return;
    try {
      await deleteAgent(id);
      setAgents((prev) => prev.filter((a) => a.id !== id));
    } catch (err: any) {
      alert(err.message ?? "Failed to delete agent");
    }
  };

  const statusCounts = agents.reduce<Record<string, number>>((acc, a) => {
    acc[a.status] = (acc[a.status] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Agents</h1>
          <p className="text-sm text-slate-500 mt-0.5">Manage your AI agents</p>
        </div>
        <Link
          href="/agents/new"
          className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white text-sm font-medium rounded-xl shadow-lg shadow-violet-500/20 transition-all"
        >
          <PlusCircle size={15} />
          New Agent
        </Link>
      </div>

      {/* Stats bar */}
      {!loading && agents.length > 0 && (
        <div className="flex gap-3 mb-6">
          {[
            { label: "Total", value: agents.length, color: "text-slate-300" },
            { label: "Ready", value: statusCounts.ready ?? 0, color: "text-emerald-400" },
            { label: "Draft", value: statusCounts.draft ?? 0, color: "text-amber-400" },
            { label: "Error", value: statusCounts.error ?? 0, color: "text-red-400" },
          ].map(({ label, value, color }) => (
            <div
              key={label}
              className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 flex items-center gap-2.5"
            >
              <span className={`text-lg font-semibold ${color}`}>{value}</span>
              <span className="text-xs text-slate-500">{label}</span>
            </div>
          ))}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => <SkeletonCard key={i} />)}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Empty */}
      {!loading && !error && agents.length === 0 && (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <div className="w-14 h-14 rounded-2xl bg-slate-800/60 border border-slate-700 flex items-center justify-center mb-4">
            <Bot size={24} className="text-slate-600" />
          </div>
          <p className="text-slate-400 font-medium mb-1">No agents yet</p>
          <p className="text-sm text-slate-600 mb-5">
            Create your first agent to get started.
          </p>
          <Link
            href="/agents/new"
            className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white text-sm font-medium rounded-xl shadow-lg shadow-violet-500/20 transition-all"
          >
            <PlusCircle size={15} />
            Create Agent
          </Link>
        </div>
      )}

      {/* Grid */}
      {!loading && !error && agents.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map((agent) => (
            <AgentCard
              key={agent.id}
              agent={agent}
              onClick={() => router.push(`/agents/${agent.id}`)}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}
    </div>
  );
}
