"use client";

interface RunStatusProps {
  status: string;
}

const statusConfig: Record<string, { color: string; dot: string }> = {
  pending: { color: "text-yellow-400", dot: "bg-yellow-400" },
  running: { color: "text-blue-400", dot: "bg-blue-400" },
  completed: { color: "text-green-400", dot: "bg-green-400" },
  failed: { color: "text-red-400", dot: "bg-red-400" },
  cancelled: { color: "text-gray-400", dot: "bg-gray-400" },
};

export default function RunStatus({ status }: RunStatusProps) {
  const config = statusConfig[status] ?? statusConfig.pending;

  return (
    <span className={`inline-flex items-center gap-2 text-sm font-medium ${config.color}`}>
      <span
        className={`w-2 h-2 rounded-full ${config.dot} ${
          status === "running" ? "animate-pulse" : ""
        }`}
      />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}
