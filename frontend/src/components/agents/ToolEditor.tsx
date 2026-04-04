"use client";

import { useState } from "react";
import { ToolDefinition } from "@/lib/types";
import { ChevronDown, ChevronRight } from "lucide-react";

interface ToolEditorProps {
  tools: ToolDefinition[];
  onUpdate?: (tools: ToolDefinition[]) => void;
}

export default function ToolEditor({ tools, onUpdate }: ToolEditorProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const toggle = (name: string) => {
    setExpanded((prev) => ({ ...prev, [name]: !prev[name] }));
  };

  if (tools.length === 0) {
    return (
      <div className="text-sm text-gray-500 py-4 text-center">
        No tools defined yet.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <label className="block text-xs font-medium text-gray-400 mb-1.5">
        Tools ({tools.length})
      </label>
      {tools.map((tool, idx) => (
        <div
          key={tool.name}
          className="border border-gray-700 rounded-lg overflow-hidden"
        >
          <button
            onClick={() => toggle(tool.name)}
            className="w-full flex items-center gap-2 px-4 py-3 bg-gray-800 hover:bg-gray-750 text-left transition-colors"
          >
            {expanded[tool.name] ? (
              <ChevronDown size={14} className="text-gray-400" />
            ) : (
              <ChevronRight size={14} className="text-gray-400" />
            )}
            <span className="text-sm font-medium text-gray-100">
              {tool.name}
            </span>
            <span className="text-xs text-gray-500 ml-auto truncate max-w-[50%]">
              {tool.description}
            </span>
          </button>
          {expanded[tool.name] && (
            <div className="p-4 bg-gray-900 border-t border-gray-700">
              <p className="text-xs text-gray-400 mb-2">
                {tool.description}
              </p>
              <p className="text-xs text-gray-500 mb-1 font-mono">
                {tool.filename}
              </p>
              <pre className="bg-gray-950 border border-gray-800 rounded-lg p-3 text-xs text-gray-300 font-mono overflow-x-auto whitespace-pre-wrap max-h-72 overflow-y-auto">
                {tool.code}
              </pre>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
