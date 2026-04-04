"use client";

import { useState } from "react";
import { Loader2, Send, Sparkles, X } from "lucide-react";
import { ToolDefinition } from "@/lib/types";
import { enhanceTool } from "@/lib/api";

interface ToolEnhanceDialogProps {
  agentId: string;
  tool: ToolDefinition;
  onAccept: (updatedTool: ToolDefinition) => void;
  onClose: () => void;
}

interface DialogMessage {
  role: "user" | "assistant";
  content: string;
  updatedTool?: ToolDefinition;
}

export default function ToolEnhanceDialog({
  agentId,
  tool,
  onAccept,
  onClose,
}: ToolEnhanceDialogProps) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<DialogMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [latestTool, setLatestTool] = useState<ToolDefinition>(tool);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");

    const userMsg: DialogMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const resp = await enhanceTool(agentId, tool.name, text);
      setLatestTool(resp.tool);
      const assistantMsg: DialogMessage = {
        role: "assistant",
        content: resp.explanation,
        updatedTool: resp.tool,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${err.message ?? "Failed to enhance tool"}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-lg w-full max-w-2xl max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-800">
          <div className="flex items-center gap-2">
            <Sparkles size={16} className="text-blue-400" />
            <h3 className="text-sm font-semibold text-gray-100">
              Enhance: {tool.name}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-300 transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Current code */}
        <div className="px-5 py-3 border-b border-gray-800">
          <p className="text-xs text-gray-500 mb-1.5">Current code</p>
          <pre className="bg-gray-950 border border-gray-800 rounded-lg p-3 text-xs text-gray-300 font-mono overflow-x-auto whitespace-pre-wrap max-h-48 overflow-y-auto">
            {latestTool.code}
          </pre>
        </div>

        {/* Chat messages */}
        <div className="flex-1 overflow-y-auto px-5 py-3 space-y-3 min-h-[120px]">
          {messages.length === 0 && (
            <p className="text-sm text-gray-500 text-center py-4">
              Describe how you want to improve this tool.
            </p>
          )}
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-800 text-gray-200"
                }`}
              >
                {msg.content}
                {msg.updatedTool && (
                  <pre className="mt-2 bg-gray-950 border border-gray-700 rounded p-2 text-xs text-gray-300 font-mono overflow-x-auto whitespace-pre-wrap max-h-32 overflow-y-auto">
                    {msg.updatedTool.code}
                  </pre>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-gray-800 rounded-lg px-3 py-2 text-sm text-gray-400">
                <span className="animate-pulse">Thinking...</span>
              </div>
            </div>
          )}
        </div>

        {/* Input bar */}
        <div className="border-t border-gray-800 px-5 py-3 flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe the enhancement..."
            disabled={loading}
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500 disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="px-3 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg transition-colors"
          >
            <Send size={14} />
          </button>
        </div>

        {/* Footer actions */}
        <div className="border-t border-gray-800 px-5 py-3 flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => onAccept(latestTool)}
            disabled={messages.length === 0}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-500 disabled:opacity-50 disabled:hover:bg-green-600 text-white text-sm font-medium rounded-lg transition-colors"
          >
            Accept
          </button>
        </div>
      </div>
    </div>
  );
}
