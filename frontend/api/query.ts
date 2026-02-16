import { api } from "@/lib/api";
import { QueryResponse, StreamEvent } from "@/types/query";

/**
 * Non-streaming query endpoint (fallback)
 */
export async function sendQuery(query: string): Promise<QueryResponse> {
  const response = await api.post<QueryResponse>("/query", { query });
  return response.data;
}

/**
 * Streaming query using Server-Sent Events (SSE)
 * Returns an async generator that yields stream events
 */
export async function* streamQuery(
  query: string,
  signal?: AbortSignal,
): AsyncGenerator<StreamEvent, void, unknown> {
  const baseURL =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  const url = `${baseURL}/query/stream`;

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query }),
    signal,
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  if (!response.body) {
    throw new Error("Response body is null");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  try {
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        break;
      }

      // Decode the chunk and add to buffer
      buffer += decoder.decode(value, { stream: true });

      // Process complete SSE messages
      const lines = buffer.split("\n");
      buffer = lines.pop() || ""; // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const jsonStr = line.slice(6); // Remove "data: " prefix
            const event: StreamEvent = JSON.parse(jsonStr);
            yield event;
          } catch (e) {
            console.error("Failed to parse SSE message:", line, e);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export const queryApi = {
  sendQuery,
  streamQuery,
};
