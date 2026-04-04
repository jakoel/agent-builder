"use client";

import { AgentDefinition } from "@/lib/types";
import { Trash2 } from "lucide-react";

interface AgentCardProps {
  agent: AgentDefinition;
  onClick: () => void;
  onDelete?: (id: string) => void;
}

const statusColors: Record<string, string> = {
  draft: "bg-yellow-500/20 text-yellow-400",
  ready: "bg-green-500/20 text-green-400",
  error: "bg-red-500/20 text-red-400",
};

export default function AgentCard({ agent, onClick, onDelete }: AgentCardProps) {
  return (
    <div
      onClick={onClick}
      className="w-full text-left bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-600 transition-colors cursor-pointer"
    >
      <div className="flex items-start justify-between mb-3">
        <h3 className="font-semibold text-white text-base truncate mr-3">
          {agent.name}
        </h3>
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${
              statusColors[agent.status] ?? "bg-gray-700 text-gray-300"
            }`}
          >
            {agent.status}
          </span>
          {onDelete && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(agent.id);
              }}
              className="p-1 text-gray-600 hover:text-red-400 hover:bg-red-400/10 rounded transition-colors"
              title="Delete agent"
            >
              <Trash2 size={14} />
            </button>
          )}
        </div>
      </div>
      <p className="text-sm text-gray-400 line-clamp-2 mb-4">
        {agent.description || "No description"}
      </p>
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span className="bg-gray-800 px-2 py-1 rounded font-mono">
          {agent.model}
        </span>
        <span>
          {new Date(agent.updated_at).toLocaleDateString()}
        </span>
      </div>
    </div>
  );
}
