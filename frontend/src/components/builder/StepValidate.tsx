"use client";

import {
  ArrowLeft,
  CheckCircle,
  Loader2,
  Play,
  Sparkles,
  XCircle,
} from "lucide-react";
import { ToolDefinition, ToolValidationResult } from "@/lib/types";

interface StepValidateProps {
  agentId: string;
  tools: ToolDefinition[];
  validationResults: ToolValidationResult[];
  onValidate: () => Promise<void>;
  onBack: () => void;
  onFinalize: () => void;
  onFixTool: (toolName: string) => void;
  validating: boolean;
  finalizing: boolean;
}

export default function StepValidate({
  agentId,
  tools,
  validationResults,
  onValidate,
  onBack,
  onFinalize,
  onFixTool,
  validating,
  finalizing,
}: StepValidateProps) {
  const passedCount = validationResults.filter(
    (r) => r.status === "pass"
  ).length;
  const totalCount = tools.length;
  const allPassed =
    validationResults.length > 0 &&
    validationResults.length === totalCount &&
    validationResults.every((r) => r.status === "pass");

  const getResult = (toolName: string) => {
    return validationResults.find((r) => r.tool_name === toolName);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-2xl mx-auto space-y-6">
          <div>
            <h2 className="text-lg font-semibold text-gray-100">
              Validate & Launch
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              Run validation on all tools before finalizing your agent.
            </p>
          </div>

          {/* Run Validation button */}
          <button
            onClick={onValidate}
            disabled={validating}
            className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:hover:bg-blue-600 text-white text-sm font-medium rounded-lg transition-colors"
          >
            {validating ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Validating...
              </>
            ) : (
              <>
                <Play size={16} />
                Run Validation
              </>
            )}
          </button>

          {/* Tool list */}
          <div className="space-y-2">
            {tools.map((tool) => {
              const result = getResult(tool.name);
              return (
                <div
                  key={tool.name}
                  className="flex items-center justify-between bg-gray-900 border border-gray-800 rounded-lg px-4 py-3"
                >
                  <div className="flex items-center gap-3">
                    {result ? (
                      result.status === "pass" ? (
                        <CheckCircle
                          size={18}
                          className="text-green-500 shrink-0"
                        />
                      ) : (
                        <XCircle
                          size={18}
                          className="text-red-500 shrink-0"
                        />
                      )
                    ) : (
                      <div className="w-[18px] h-[18px] rounded-full border-2 border-gray-600 shrink-0" />
                    )}
                    <div>
                      <p className="text-sm font-medium text-gray-100">
                        {tool.name}
                      </p>
                      {result && result.status === "pass" && (
                        <p className="text-xs text-green-400">Valid</p>
                      )}
                      {result && result.status === "fail" && (
                        <p className="text-xs text-red-400">
                          {result.error ?? "Validation failed"}
                        </p>
                      )}
                    </div>
                  </div>
                  {result && result.status === "fail" && (
                    <button
                      onClick={() => onFixTool(tool.name)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-blue-400 hover:text-blue-300 border border-blue-500/30 hover:border-blue-500/50 rounded-lg transition-colors"
                    >
                      <Sparkles size={12} />
                      Fix with AI
                    </button>
                  )}
                </div>
              );
            })}
          </div>

          {/* Summary */}
          {validationResults.length > 0 && (
            <p className="text-sm text-gray-400">
              {passedCount} of {totalCount} tools passed
            </p>
          )}
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
          onClick={onFinalize}
          disabled={!allPassed || finalizing}
          className="flex items-center gap-2 px-5 py-2.5 bg-green-600 hover:bg-green-500 disabled:opacity-50 disabled:hover:bg-green-600 text-white text-sm font-medium rounded-lg transition-colors"
        >
          {finalizing ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              Finalizing...
            </>
          ) : (
            <>
              <CheckCircle size={16} />
              Finalize Agent
            </>
          )}
        </button>
      </div>
    </div>
  );
}
