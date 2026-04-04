"use client";

import { useRouter } from "next/navigation";
import { RunResult } from "@/lib/types";
import RunStatus from "./RunStatus";

interface RunHistoryProps {
  runs: RunResult[];
}

function formatDuration(started: string, completed?: string): string {
  if (!completed) return "-";
  const ms =
    new Date(completed).getTime() - new Date(started).getTime();
  if (ms < 1000) return `${ms}ms`;
  const secs = Math.round(ms / 1000);
  if (secs < 60) return `${secs}s`;
  const mins = Math.floor(secs / 60);
  const remSecs = secs % 60;
  return `${mins}m ${remSecs}s`;
}

export default function RunHistory({ runs }: RunHistoryProps) {
  const router = useRouter();

  if (runs.length === 0) {
    return (
      <div className="text-sm text-gray-500 py-8 text-center">
        No runs found.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-500 border-b border-gray-800">
            <th className="pb-3 pr-4 font-medium">Run ID</th>
            <th className="pb-3 pr-4 font-medium">Status</th>
            <th className="pb-3 pr-4 font-medium">Started</th>
            <th className="pb-3 font-medium">Duration</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr
              key={run.run_id}
              onClick={() =>
                router.push(`/agents/${run.agent_id}`)
              }
              className="border-b border-gray-800/50 hover:bg-gray-900 cursor-pointer transition-colors"
            >
              <td className="py-3 pr-4 font-mono text-gray-300">
                {run.run_id.slice(0, 8)}...
              </td>
              <td className="py-3 pr-4">
                <RunStatus status={run.status} />
              </td>
              <td className="py-3 pr-4 text-gray-400">
                {new Date(run.started_at).toLocaleString()}
              </td>
              <td className="py-3 text-gray-400">
                {formatDuration(run.started_at, run.completed_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
