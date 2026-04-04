"use client";

import { useEffect, useState } from "react";
import { OllamaModel } from "../types";
import { getModels } from "../api";

export function useModels() {
  const [models, setModels] = useState<OllamaModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getModels();
        if (!cancelled) setModels(data);
      } catch (err: any) {
        if (!cancelled) setError(err.message ?? "Failed to fetch models");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return { models, loading, error };
}
