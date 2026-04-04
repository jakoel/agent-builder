"use client";

import { useCallback, useEffect, useState } from "react";
import { AgentDefinition } from "../types";
import { getAgent } from "../api";

export function useAgent(id: string | undefined) {
  const [agent, setAgent] = useState<AgentDefinition | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAgent = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getAgent(id);
      setAgent(data);
    } catch (err: any) {
      setError(err.message ?? "Failed to fetch agent");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchAgent();
  }, [fetchAgent]);

  return { agent, loading, error, refetch: fetchAgent };
}
