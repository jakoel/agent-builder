"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AgentDefinition } from "@/lib/types";
import { getAgents, deleteAgent } from "@/lib/api";
import AgentCard from "@/components/agents/AgentCard";
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

  useEffect(() => {
    loadAgents();
  }, []);

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this agent? This cannot be undone.")) return;
    try {
      await deleteAgent(id);
      setAgents((prev) => prev.filter((a) => a.id !== id));
    } catch (err: any) {
      alert(err.message ?? "Failed to delete agent");
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Agents</h1>
          <p className="text-sm text-gray-400 mt-1">
            Manage your AI agents
          </p>
        </div>
        <Link
          href="/agents/new"
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <PlusCircle size={16} />
          Create New Agent
        </Link>
      </div>

      {loading && (
        <div className="text-center py-20 text-gray-500">Loading...</div>
      )}

      {error && (
        <div className="text-center py-20 text-red-400">{error}</div>
      )}

      {!loading && !error && agents.length === 0 && (
        <div className="text-center py-20">
          <Bot size={48} className="mx-auto text-gray-700 mb-4" />
          <p className="text-gray-400 mb-2">No agents yet</p>
          <p className="text-sm text-gray-500">
            Create your first agent to get started.
          </p>
        </div>
      )}

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
