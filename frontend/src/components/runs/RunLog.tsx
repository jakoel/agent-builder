"use client";

import { useEffect, useRef } from "react";
import { RunLog as RunLogType } from "@/lib/types";

interface RunLogProps {
  logs: RunLogType[];
}

const levelStyles: Record<string, { text: string; label: string }> = {
  info:    { text: "text-blue-400",    label: "bg-blue-500/10 text-blue-400" },
  debug:   { text: "text-slate-500",   label: "bg-slate-700/40 text-slate-500" },
  warning: { text: "text-amber-400",   label: "bg-amber-500/10 text-amber-400" },
  error:   { text: "text-red-400",     label: "bg-red-500/10 text-red-400" },
  success: { text: "text-emerald-400", label: "bg-emerald-500/10 text-emerald-400" },
};

export default function RunLogViewer({ logs }: RunLogProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  if (logs.length === 0) {
    return (
      <div className="text-xs text-slate-600 py-6 text-center bg-slate-900/50 border border-slate-800 rounded-xl">
        No log entries yet.
      </div>
    );
  }

  return (
    <div className="bg-slate-950 border border-slate-800 rounded-xl p-3 max-h-96 overflow-y-auto font-mono text-xs space-y-1">
      {logs.map((log, i) => {
        const style = levelStyles[log.level] ?? levelStyles.info;
        const time = new Date(log.timestamp).toLocaleTimeString("en-US", {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        });
        return (
          <div key={i} className="flex gap-2.5 items-start py-0.5">
            <span className="text-slate-600 whitespace-nowrap shrink-0">{time}</span>
            <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider shrink-0 ${style.label}`}>
              {log.level}
            </span>
            <span className="text-slate-600 shrink-0">[{log.node_id}]</span>
            <span className="text-slate-300 break-all">{log.message}</span>
          </div>
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
}
