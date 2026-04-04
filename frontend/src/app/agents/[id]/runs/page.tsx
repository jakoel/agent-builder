"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { RunResult } from "@/lib/types";
import { getRuns } from "@/lib/api";
import { useAgent } from "@/lib/hooks/useAgent";
import RunHistory from "@/components/runs/RunHistory";

export default function AgentRunsPage() {
  const params = useParams();
  const id = params.id as string;
  const { agent } = useAgent(id);
  const [runs, setRuns] = useState<RunResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    (async () => {
      try {
        const data = await getRuns(id);
        setRuns(data);
      } catch (err: any) {
        setError(err.message ?? "Failed to load runs");
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">
          {agent ? `${agent.name} - Run History` : "Agent Run History"}
        </h1>
        <p className="text-sm text-gray-400 mt-1">
          Runs for this agent
        </p>
      </div>

      {loading && (
        <div className="text-center py-20 text-gray-500">Loading...</div>
      )}

      {error && (
        <div className="text-center py-20 text-red-400">{error}</div>
      )}

      {!loading && !error && <RunHistory runs={runs} />}
    </div>
  );
}
