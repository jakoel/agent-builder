"use client";

import { useEffect, useRef, useState } from "react";
import { RunResult, RunLog } from "../types";

const BASE_URL = "http://localhost:8000";

export function useRun(runId: string | null) {
  const [run, setRun] = useState<RunResult | null>(null);
  const [liveOutput, setLiveOutput] = useState<string>("");
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!runId) {
      setLiveOutput("");
      return;
    }

    const es = new EventSource(`${BASE_URL}/api/runs/${runId}/stream`);
    esRef.current = es;

    es.onopen = () => {
      setConnected(true);
      setError(null);
    };

    es.addEventListener("log", (event) => {
      try {
        const log: RunLog = JSON.parse(event.data);
        setRun((prev) => {
          if (!prev) return prev;
          return { ...prev, logs: [...prev.logs, log] };
        });
      } catch {}
    });

    es.addEventListener("status", (event) => {
      try {
        const update = JSON.parse(event.data);
        setRun((prev) => {
          if (!prev) return { ...update, logs: update.logs ?? [] } as RunResult;
          return { ...prev, ...update };
        });
      } catch {}
    });

    es.addEventListener("live", (event) => {
      try {
        const { text } = JSON.parse(event.data);
        setLiveOutput(text ?? "");
      } catch {}
    });

    es.addEventListener("done", (event) => {
      try {
        const result: RunResult = JSON.parse(event.data);
        setRun(result);
        setLiveOutput("");
      } catch {}
    });

    es.onerror = () => {
      setConnected(false);
      setError("Connection lost");
      es.close();
    };

    return () => {
      es.close();
      esRef.current = null;
      setConnected(false);
      setLiveOutput("");
    };
  }, [runId]);

  return { run, liveOutput, connected, error };
}
