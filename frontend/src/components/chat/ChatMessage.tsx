"use client";

import { BuilderMessage } from "@/lib/types";

interface ChatMessageProps {
  message: BuilderMessage;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  const artifactBadges: string[] = [];
  if (message.artifacts) {
    if (message.artifacts.system_prompt) artifactBadges.push("System Prompt");
    if (message.artifacts.tools && message.artifacts.tools.length > 0) {
      artifactBadges.push(
        `${message.artifacts.tools.length} Tool${
          message.artifacts.tools.length > 1 ? "s" : ""
        }`
      );
    }
    if (message.artifacts.flow) artifactBadges.push("Flow");
  }

  return (
    <div
      className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}
    >
      <div
        className={`max-w-[80%] rounded-xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "bg-blue-600 text-white"
            : "bg-gray-800 text-gray-100"
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {artifactBadges.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2 pt-2 border-t border-white/10">
            {artifactBadges.map((badge) => (
              <span
                key={badge}
                className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-white/10 text-white/70"
              >
                {badge}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
