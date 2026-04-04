"use client";

import { useCallback, useState } from "react";
import { BuilderMessage } from "../types";
import { sendBuilderMessage } from "../api";

export function useChat(agentId: string | null) {
  const [messages, setMessages] = useState<BuilderMessage[]>([]);
  const [loading, setLoading] = useState(false);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!agentId) return;

      const userMsg: BuilderMessage = { role: "user", content: text };
      setMessages((prev) => [...prev, userMsg]);
      setLoading(true);

      try {
        const assistantMsg = await sendBuilderMessage(agentId, text);
        setMessages((prev) => [...prev, assistantMsg]);
      } catch (err: any) {
        const errorMsg: BuilderMessage = {
          role: "assistant",
          content: `Error: ${err.message ?? "Failed to send message"}`,
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setLoading(false);
      }
    },
    [agentId]
  );

  const addMessage = useCallback((msg: BuilderMessage) => {
    setMessages((prev) => [...prev, msg]);
  }, []);

  return { messages, loading, sendMessage, addMessage };
}
