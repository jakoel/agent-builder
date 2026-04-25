"use client";

import { AgentDefinition } from "@/lib/types";
import { Bot, Trash2, Wrench } from "lucide-react";

interface AgentCardProps {
  agent: AgentDefinition;
  onClick: () => void;
  onDelete?: (id: string) => void;
}

const statusConfig: Record<string, { bg: string; text: string; dot: string }> = {
  draft:  { bg: "bg-amber-500/10",  text: "text-amber-400",  dot: "bg-amber-400" },
  ready:  { bg: "bg-emerald-500/10", text: "text-emerald-400", dot: "bg-emerald-400" },
  error:  { bg: "bg-red-500/10",    text: "text-red-400",    dot: "bg-red-400" },
};

export default function AgentCard({ agent, onClick, onDelete }: AgentCardProps) {
  const status = statusConfig[agent.status] ?? statusConfig.draft;

  return (
    <div
      onClick={onClick}
      className="group relative bg-slate-900 border border-slate-800 rounded-2xl p-5 hover:border-slate-700 hover:shadow-xl hover:shadow-black/30 transition-all duration-200 cursor-pointer"
    >
      {/* Top row */}
      <div className="flex items-start justify-between mb-4">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500/20 to-indigo-500/20 border border-violet-500/20 flex items-center justify-center shrink-0">
          <Bot size={16} className="text-violet-400" />
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${status.bg} ${status.text} border-current/20`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${status.dot}`} />
            {agent.status}
          </span>
          {onDelete && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(agent.id);
              }}
              className="p-1.5 text-slate-600 hover:text-red-400 hover:bg-red-400/10 rounded-lg opacity-0 group-hover:opacity-100 transition-all"
              title="Delete agent"
            >
              <Trash2 size={13} />
            </button>
          )}
        </div>
      </div>

      {/* Name + description */}
      <h3 className="font-semibold text-slate-100 text-sm mb-1.5 truncate">
        {agent.name}
      </h3>
      <p className="text-xs text-slate-500 line-clamp-2 leading-relaxed mb-4">
        {agent.description || "No description"}
      </p>

      {/* Footer */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs text-slate-500 bg-slate-800/60 px-2.5 py-1 rounded-lg font-mono">
          {agent.model}
        </div>
        <div className="flex items-center gap-1 text-xs text-slate-600">
          <Wrench size={11} />
          <span>{agent.tools.length} tools</span>
        </div>
      </div>
    </div>
  );
}
