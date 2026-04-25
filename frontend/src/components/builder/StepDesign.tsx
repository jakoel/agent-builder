"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, Check, Loader2, Send } from "lucide-react";
import { sendBuilderMessage, getToolDetail } from "@/lib/api";
import { ToolDefinition, FlowDefinition, SuggestedTool } from "@/lib/types";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface ChatMsg {
  role: "user" | "assistant";
  content: string;
}

type DesignPhase =
  | "ask_prompt"
  | "refining_prompt"
  | "prompt_review"
  | "suggesting_tools"
  | "tools_review"
  | "generating_tool"
  | "tool_review"
  | "done";


interface StepDesignProps {
  agentId: string;
  onNext: (artifacts: {
    systemPrompt: string;
    tools: ToolDefinition[];
    flow?: FlowDefinition;
  }) => void;
  onBack: () => void;
}

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

const APPROVAL_PHRASES = [
  "approve",
  "approved",
  "looks good",
  "lgtm",
  "yes",
  "ok",
  "perfect",
  "great",
  "proceed",
  "go ahead",
  "accept",
  "ship it",
  "y",
  "sure",
  "continue",
];

function isApproval(text: string): boolean {
  const lower = text.toLowerCase().trim();
  return APPROVAL_PHRASES.includes(lower);
}

function formatToolList(tools: SuggestedTool[]): string {
  if (!tools.length) return "No tools suggested.";
  return tools
    .map((t, i) => {
      const tag = t.prebuilt ? " (pre-built)" : " (custom)";
      return `${i + 1}. **${t.name}**${tag} — ${t.description}`;
    })
    .join("\n");
}

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export default function StepDesign({ agentId, onNext, onBack }: StepDesignProps) {
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [phase, setPhase] = useState<DesignPhase>("ask_prompt");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Artifacts being built up
  const [systemPrompt, setSystemPrompt] = useState("");
  const [suggestedTools, setSuggestedTools] = useState<SuggestedTool[]>([]);
  const [generatedTools, setGeneratedTools] = useState<ToolDefinition[]>([]);
  const [currentToolIndex, setCurrentToolIndex] = useState(0);
  const [currentToolCode, setCurrentToolCode] = useState("");

  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  // Initial bot message
  useEffect(() => {
    addBot(
      "Describe the skeleton of the system prompt for your agent. What should it do and how should it behave?"
    );
  }, []);

  // Focus input when loading finishes
  useEffect(() => {
    if (!loading) inputRef.current?.focus();
  }, [loading]);

  /* ---- Message helpers ---- */

  function addBot(content: string) {
    setMessages((prev) => [...prev, { role: "assistant", content }]);
  }

  function addUser(content: string) {
    setMessages((prev) => [...prev, { role: "user", content }]);
  }

  /* ---- Core send handler ---- */

  async function handleSend(text?: string) {
    const msg = (text ?? input).trim();
    if (!msg || loading) return;
    setInput("");
    setError(null);
    addUser(msg);

    try {
      switch (phase) {
        case "ask_prompt":
          await doRefinePrompt(msg, "");
          break;

        case "prompt_review":
          if (isApproval(msg)) {
            await doSuggestTools();
          } else {
            await doRefinePrompt(msg, systemPrompt);
          }
          break;

        case "tools_review":
          if (isApproval(msg)) {
            await doStartToolGeneration();
          } else {
            await doRefineToolList(msg);
          }
          break;

        case "tool_review":
          if (isApproval(msg)) {
            await doApproveCurrentTool();
          } else {
            await doRegenerateTool(msg);
          }
          break;

        default:
          break;
      }
    } catch (err: any) {
      const detail = err?.message ?? "Something went wrong";
      setError(detail);
      addBot(`Something went wrong: ${detail}. Please try again.`);
      // Revert to previous review phase so user can retry
      if (phase === "refining_prompt") setPhase("ask_prompt");
      if (phase === "suggesting_tools") setPhase("prompt_review");
      if (phase === "generating_tool") setPhase("tools_review");
    }
  }

  /* ---- Phase actions ---- */

  async function doRefinePrompt(userMsg: string, currentDraft: string) {
    setPhase("refining_prompt");
    setLoading(true);

    const resp = await sendBuilderMessage(agentId, userMsg, "refine_prompt", {
      current_draft: currentDraft,
    });

    const refined = resp.artifacts?.system_prompt ?? resp.content;
    setSystemPrompt(refined);
    setLoading(false);
    setPhase("prompt_review");

    addBot(
      `Here's your refined system prompt:\n\n---\n${refined}\n---\n\nWould you like to modify it, or type **approve** to continue?`
    );
  }

  async function doSuggestTools() {
    addBot("System prompt approved! Let me suggest tools for your agent...");
    setPhase("suggesting_tools");
    setLoading(true);

    const resp = await sendBuilderMessage(
      agentId,
      "Suggest tools based on the system prompt",
      "suggest_tools",
      { system_prompt: systemPrompt }
    );

    const tools: SuggestedTool[] = resp.artifacts?.suggested_tools ?? [];
    setSuggestedTools(tools);
    setLoading(false);
    setPhase("tools_review");

    if (tools.length > 0) {
      addBot(
        `Here are the tools I suggest:\n\n${formatToolList(tools)}\n\nWould you like to modify the list, or type **approve** to continue?`
      );
    } else {
      addBot(
        "I couldn't parse a tool list from the model's response. Could you describe the tools you need?"
      );
    }
  }

  async function doRefineToolList(userMsg: string) {
    setPhase("suggesting_tools");
    setLoading(true);

    const resp = await sendBuilderMessage(agentId, userMsg, "suggest_tools", {
      system_prompt: systemPrompt,
      current_tools: suggestedTools,
    });

    const tools: SuggestedTool[] = resp.artifacts?.suggested_tools ?? suggestedTools;
    setSuggestedTools(tools);
    setLoading(false);
    setPhase("tools_review");

    addBot(
      `Updated tool list:\n\n${formatToolList(tools)}\n\nWould you like to modify further, or type **approve** to continue?`
    );
  }

  async function doStartToolGeneration() {
    if (suggestedTools.length === 0) {
      addBot("No tools to generate. You can go back and add some, or proceed to the next step.");
      setPhase("done");
      return;
    }

    setGeneratedTools([]);
    setCurrentToolIndex(0);
    addBot(
      `Tool list approved! I'll now set up each tool one by one.\n\nStarting with **${suggestedTools[0].name}**...`
    );
    await doGenerateTool(0);
  }

  async function doGenerateTool(index: number) {
    const tool = suggestedTools[index];
    setPhase("generating_tool");
    setLoading(true);
    setCurrentToolIndex(index);

    if (tool.prebuilt) {
      // Load pre-built tool from the library — no LLM generation needed
      try {
        const detail = await getToolDetail(tool.name);
        const code = detail.code ?? "";
        const params = detail.parameters ?? tool.parameters ?? {};
        setCurrentToolCode(code);
        setLoading(false);
        setPhase("tool_review");
        addBot(
          `**${tool.name}** (${index + 1}/${suggestedTools.length}) is a **pre-built** tool — ready to use:\n\n\`\`\`python\n${code}\n\`\`\`\n\nApprove this tool, or describe what to change.`
        );
        // Update parameters from the library definition
        setSuggestedTools((prev) =>
          prev.map((t, i) => (i === index ? { ...t, parameters: params } : t))
        );
      } catch {
        // Fallback: if the prebuilt tool can't be loaded, generate it
        addBot(`Could not load pre-built **${tool.name}**, generating custom code instead...`);
        await doGenerateCustomTool(index);
      }
    } else {
      await doGenerateCustomTool(index);
    }
  }

  async function doGenerateCustomTool(index: number) {
    const tool = suggestedTools[index];

    const resp = await sendBuilderMessage(agentId, "", "generate_tool_code", {
      tool_name: tool.name,
      tool_description: tool.description,
      tool_parameters: tool.parameters ?? {},
    });

    const code = resp.artifacts?.tool?.code ?? resp.content;
    setCurrentToolCode(code);
    setLoading(false);
    setPhase("tool_review");

    addBot(
      `Here's the generated code for **${tool.name}** (${index + 1}/${suggestedTools.length}):\n\n\`\`\`python\n${code}\n\`\`\`\n\nApprove this tool, or describe what to change.`
    );
  }

  async function doApproveCurrentTool() {
    const tool = suggestedTools[currentToolIndex];
    const toolDef: ToolDefinition = {
      name: tool.name,
      description: tool.description,
      parameters: tool.parameters ?? {},
      code: currentToolCode,
      filename: `${tool.name}.py`,
    };

    // For prebuilt tools, persist to agent via the generate_tool_code endpoint
    // (it saves the tool definition to disk)
    if (tool.prebuilt) {
      try {
        await sendBuilderMessage(agentId, "Save prebuilt tool", "generate_tool_code", {
          tool_name: tool.name,
          tool_description: tool.description,
          tool_parameters: tool.parameters ?? {},
          prebuilt_code: currentToolCode,
        });
      } catch {
        // Non-critical — tool is still in local state
      }
    }

    const updated = [...generatedTools, toolDef];
    setGeneratedTools(updated);

    const nextIndex = currentToolIndex + 1;
    if (nextIndex < suggestedTools.length) {
      addBot(
        `**${tool.name}** approved! Next up: **${suggestedTools[nextIndex].name}**...`
      );
      await doGenerateTool(nextIndex);
    } else {
      addBot(
        `All ${suggestedTools.length} tools set up and approved! Click **Next** to review everything.`
      );
      setPhase("done");
    }
  }

  async function doRegenerateTool(userMsg: string) {
    const tool = suggestedTools[currentToolIndex];
    setPhase("generating_tool");
    setLoading(true);

    const resp = await sendBuilderMessage(agentId, userMsg, "generate_tool_code", {
      tool_name: tool.name,
      tool_description: tool.description,
      tool_parameters: tool.parameters ?? {},
      current_code: currentToolCode,
    });

    const code = resp.artifacts?.tool?.code ?? resp.content;
    setCurrentToolCode(code);
    setLoading(false);
    setPhase("tool_review");

    addBot(
      `Here's the updated code for **${tool.name}**:\n\n\`\`\`python\n${code}\n\`\`\`\n\nApprove this tool, or describe what to change.`
    );
  }

  /* ---- Proceed to next wizard step ---- */

  function handleNext() {
    onNext({
      systemPrompt,
      tools: generatedTools,
    });
  }

  /* ---- Approval button handler ---- */

  function handleApprove() {
    handleSend("approve");
  }

  /* ---- Rendering ---- */

  const isReviewPhase =
    phase === "prompt_review" ||
    phase === "tools_review" ||
    phase === "tool_review";

  return (
    <div className="flex flex-col h-full">
      {/* Chat messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[75%] rounded-xl px-4 py-3 text-sm whitespace-pre-wrap ${
                msg.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-800 text-gray-200"
              }`}
            >
              <MessageContent content={msg.content} />
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-800 rounded-xl px-4 py-3 text-sm text-gray-400 flex items-center gap-2">
              <Loader2 size={14} className="animate-spin" />
              Thinking...
            </div>
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="border-t border-gray-800 px-4 py-3 space-y-2 bg-gray-950">
        {error && (
          <p className="text-xs text-red-400 px-1">{error}</p>
        )}

        {isReviewPhase && (
          <button
            onClick={handleApprove}
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-green-600/20 hover:bg-green-600/30 text-green-400 text-sm font-medium rounded-lg border border-green-600/30 transition-colors disabled:opacity-50"
          >
            <Check size={14} />
            Approve & Continue
          </button>
        )}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-2"
        >
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading || phase === "done"}
            placeholder={
              phase === "done"
                ? "All done — click Next to continue"
                : isReviewPhase
                ? "Describe changes, or click Approve above..."
                : "Type your message..."
            }
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={loading || !input.trim() || phase === "done"}
            className="p-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:hover:bg-blue-600 text-white rounded-lg transition-colors"
          >
            <Send size={16} />
          </button>
        </form>
      </div>

      {/* Bottom nav */}
      <div className="border-t border-gray-800 px-4 py-3 flex items-center justify-between bg-gray-950">
        <button
          onClick={onBack}
          className="flex items-center gap-2 px-4 py-2 text-sm text-gray-400 hover:text-gray-200 transition-colors"
        >
          <ArrowLeft size={16} />
          Back
        </button>
        <button
          onClick={handleNext}
          disabled={phase !== "done"}
          className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:hover:bg-blue-600 text-white text-sm font-medium rounded-lg transition-colors"
        >
          Next
          <ArrowRight size={16} />
        </button>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Simple message renderer (bold + code blocks)                        */
/* ------------------------------------------------------------------ */

function MessageContent({ content }: { content: string }) {
  // Split by code fences
  const parts = content.split(/(```[\s\S]*?```)/g);

  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith("```")) {
          // Extract language hint and code
          const match = part.match(/```(\w*)\n?([\s\S]*?)```/);
          const code = match ? match[2] : part.slice(3, -3);
          return (
            <pre
              key={i}
              className="bg-gray-950 border border-gray-700 rounded-lg p-3 my-2 text-xs font-mono overflow-x-auto whitespace-pre"
            >
              {code.trim()}
            </pre>
          );
        }

        // Handle **bold** and --- separators
        const segments = part.split(/(\*\*[^*]+\*\*|^---$)/gm);
        return (
          <span key={i}>
            {segments.map((seg, j) => {
              if (seg.startsWith("**") && seg.endsWith("**")) {
                return (
                  <strong key={j} className="font-semibold text-white">
                    {seg.slice(2, -2)}
                  </strong>
                );
              }
              if (seg === "---") {
                return <hr key={j} className="border-gray-700 my-2" />;
              }
              return <span key={j}>{seg}</span>;
            })}
          </span>
        );
      })}
    </>
  );
}
