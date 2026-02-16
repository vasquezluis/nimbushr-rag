import { useRef, useState, useCallback } from "react";
import { streamQuery } from "@/api/query";
import { Source, UseStreamingQueryResult } from "@/types/query";

export function useStreamingQuery(): UseStreamingQueryResult {
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [streamingAnswer, setStreamingAnswer] = useState("");
  const [sources, setSources] = useState<Source[]>([]);
  const [status, setStatus] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

  const cancel = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsStreaming(false);
      setStatus(null);
    }
  }, []);

  const sendStreamingQuery = useCallback(async (query: string) => {
    // Reset state
    setIsStreaming(true);
    setError(null);
    setStreamingAnswer("");
    setSources([]);
    setStatus("Starting...");

    // Create new abort controller
    abortControllerRef.current = new AbortController();

    try {
      const stream = streamQuery(query, abortControllerRef.current.signal);

      for await (const event of stream) {
        switch (event.type) {
          case "status":
            setStatus(event.data);
            break;

          case "sources":
            setSources(event.data);
            setStatus(null);
            break;

          case "token":
            setStreamingAnswer((prev) => prev + event.data);
            break;

          case "done":
            setIsStreaming(false);
            setStatus(null);
            break;

          case "error":
            setError(event.data);
            setIsStreaming(false);
            setStatus(null);
            break;
        }
      }
    } catch (err: any) {
      if (err.name === "AbortError") {
        console.log("Stream cancelled by user");
      } else {
        console.error("Streaming error:", err);
        setError(err.message || "An error occurred during streaming");
      }
      setIsStreaming(false);
      setStatus(null);
    } finally {
      abortControllerRef.current = null;
    }
  }, []);

  return {
    sendStreamingQuery,
    cancel,
    isStreaming,
    error,
    streamingAnswer,
    sources,
    status,
  };
}
