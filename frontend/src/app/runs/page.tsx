"use client";

import { useEffect, useState } from "react";
import { RunResult, AgentDefinition } from "@/lib/types";
import { getRuns, getAgents } from "@/lib/api";
import RunHistory from "@/components/runs/RunHistory";
import { Skeleton } from "@/components/ui/Skeleton";

export default function RunsPage() {
  const [runs, setRuns] = useState<RunResult[]>([]);
  const [agentMap, setAgentMap] = useState<Record<string, AgentDefinition>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [runsData, agentsData] = await Promise.all([getRuns(), getAgents()]);
        setRuns(runsData);
        setAgentMap(Object.fromEntries(agentsData.map((a) => [a.id, a])));
      } catch (err: any) {
        setError(err.message ?? "Failed to load");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-slate-100">Run History</h1>
        <p className="text-sm text-slate-500 mt-0.5">All agent runs across the platform</p>
      </div>

      {loading && (
        <div className="space-y-2">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-14 w-full rounded-xl" />
          ))}
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-sm text-red-400">
          {error}
        </div>
      )}

      {!loading && !error && <RunHistory runs={runs} agentMap={agentMap} />}
    </div>
  );
}
