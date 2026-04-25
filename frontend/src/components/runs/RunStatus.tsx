"use client";

interface RunStatusProps {
  status: string;
}

const statusConfig: Record<string, { bg: string; text: string; dot: string; ring?: string }> = {
  pending:   { bg: "bg-amber-500/10",   text: "text-amber-400",   dot: "bg-amber-400" },
  running:   { bg: "bg-blue-500/10",    text: "text-blue-400",    dot: "bg-blue-400",    ring: "bg-blue-400" },
  completed: { bg: "bg-emerald-500/10", text: "text-emerald-400", dot: "bg-emerald-400" },
  failed:    { bg: "bg-red-500/10",     text: "text-red-400",     dot: "bg-red-400" },
  cancelled: { bg: "bg-slate-700/40",   text: "text-slate-400",   dot: "bg-slate-500" },
  draft:     { bg: "bg-amber-500/10",   text: "text-amber-400",   dot: "bg-amber-400" },
  ready:     { bg: "bg-emerald-500/10", text: "text-emerald-400", dot: "bg-emerald-400" },
  error:     { bg: "bg-red-500/10",     text: "text-red-400",     dot: "bg-red-400" },
};

export default function RunStatus({ status }: RunStatusProps) {
  const cfg = statusConfig[status] ?? statusConfig.pending;
  const isRunning = status === "running";

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${cfg.bg} ${cfg.text}`}
    >
      <span className="relative flex h-1.5 w-1.5">
        {isRunning && (
          <span
            className={`animate-ping absolute inline-flex h-full w-full rounded-full ${cfg.ring} opacity-75`}
          />
        )}
        <span className={`relative inline-flex rounded-full h-1.5 w-1.5 ${cfg.dot}`} />
      </span>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}
