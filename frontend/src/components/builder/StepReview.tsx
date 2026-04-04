"use client";

import { useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle,
  ChevronDown,
  ChevronRight,
  Sparkles,
  XCircle,
} from "lucide-react";
import PromptEditor from "@/components/agents/PromptEditor";
import FlowVisualization from "@/components/flow/FlowVisualization";
import { ToolDefinition, FlowDefinition, ToolValidationResult } from "@/lib/types";

interface StepReviewProps {
  agentId: string;
  artifacts: {
    systemPrompt: string;
    tools: ToolDefinition[];
    flow?: FlowDefinition;
  };
  validationResults: ToolValidationResult[];
  onToolUpdate: (tools: ToolDefinition[]) => void;
  onBack: () => void;
  onNext: () => void;
  onEnhanceTool?: (tool: ToolDefinition) => void;
}

export default function StepReview({
  agentId,
  artifacts,
  validationResults,
  onToolUpdate,
  onBack,
  onNext,
  onEnhanceTool,
}: StepReviewProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const toggle = (name: string) => {
    setExpanded((prev) => ({ ...prev, [name]: !prev[name] }));
  };

  const getValidation = (toolName: string) => {
    return validationResults.find((r) => r.tool_name === toolName);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* System Prompt Section */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
          <h3 className="text-sm font-semibold text-gray-200 mb-3">
            System Prompt
          </h3>
          <PromptEditor value={artifacts.systemPrompt} readOnly />
        </div>

        {/* Tools Section */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
          <h3 className="text-sm font-semibold text-gray-200 mb-3">
            Tools ({artifacts.tools.length})
          </h3>
          {artifacts.tools.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-4">
              No tools defined.
            </p>
          ) : (
            <div className="space-y-2">
              {artifacts.tools.map((tool) => {
                const validation = getValidation(tool.name);
                return (
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
                      <span className="text-xs text-gray-500 truncate max-w-[30%]">
                        {tool.description}
                      </span>
                      <span className="ml-auto flex items-center gap-2">
                        {validation ? (
                          validation.status === "pass" ? (
                            <span className="flex items-center gap-1 text-xs text-green-400">
                              <CheckCircle size={14} />
                              Valid
                            </span>
                          ) : (
                            <span className="flex items-center gap-1 text-xs text-red-400">
                              <XCircle size={14} />
                              {validation.error ?? "Failed"}
                            </span>
                          )
                        ) : (
                          <span className="text-xs text-gray-500">
                            Not yet validated
                          </span>
                        )}
                      </span>
                    </button>
                    {expanded[tool.name] && (
                      <div className="p-4 bg-gray-900 border-t border-gray-700 space-y-3">
                        <p className="text-xs text-gray-400">
                          {tool.description}
                        </p>
                        <pre className="bg-gray-950 border border-gray-800 rounded-lg p-3 text-xs text-gray-300 font-mono overflow-x-auto whitespace-pre-wrap max-h-72 overflow-y-auto">
                          {tool.code}
                        </pre>
                        {onEnhanceTool && (
                          <button
                            onClick={() => onEnhanceTool(tool)}
                            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-blue-400 hover:text-blue-300 border border-blue-500/30 hover:border-blue-500/50 rounded-lg transition-colors"
                          >
                            <Sparkles size={12} />
                            Enhance with AI
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Flow Section */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
          <h3 className="text-sm font-semibold text-gray-200 mb-3">Flow</h3>
          <FlowVisualization flow={artifacts.flow} />
        </div>
      </div>

      {/* Bottom bar */}
      <div className="border-t border-gray-800 px-4 py-3 flex items-center justify-between bg-gray-950">
        <button
          onClick={onBack}
          className="flex items-center gap-2 px-4 py-2 text-sm text-gray-400 hover:text-gray-200 transition-colors"
        >
          <ArrowLeft size={16} />
          Back
        </button>
        <button
          onClick={onNext}
          className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
        >
          Continue to Validation
          <ArrowRight size={16} />
        </button>
      </div>
    </div>
  );
}
