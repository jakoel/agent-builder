"use client";

import { useEffect, useRef } from "react";
import { RunLog as RunLogType } from "@/lib/types";

interface RunLogProps {
  logs: RunLogType[];
}

const levelColors: Record<string, string> = {
  info: "text-blue-400",
  debug: "text-gray-500",
  warning: "text-yellow-400",
  error: "text-red-400",
  success: "text-green-400",
};

export default function RunLogViewer({ logs }: RunLogProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  if (logs.length === 0) {
    return (
      <div className="text-sm text-gray-500 py-4 text-center">
        No logs yet.
      </div>
    );
  }

  return (
    <div className="bg-gray-950 border border-gray-800 rounded-lg p-3 max-h-96 overflow-y-auto font-mono text-xs space-y-1">
      {logs.map((log, i) => {
        const color = levelColors[log.level] ?? "text-gray-400";
        const time = new Date(log.timestamp).toLocaleTimeString();
        return (
          <div key={i} className="flex gap-3">
            <span className="text-gray-600 whitespace-nowrap">{time}</span>
            <span className={`uppercase w-12 shrink-0 ${color}`}>
              {log.level}
            </span>
            <span className="text-gray-500 shrink-0">[{log.node_id}]</span>
            <span className="text-gray-300">{log.message}</span>
          </div>
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
}
