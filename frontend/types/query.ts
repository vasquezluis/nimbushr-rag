export interface QueryRequest {
  query: string;
}

export interface Source {
  file: string;
  chunk_index: number;
  has_tables: boolean;
  has_images: boolean;
  ai_summarized: boolean;
}

export interface QueryResponse {
  answer: string;
  sources: Array<Source>;
  num_chunks: number;
  chunks_reranked?: boolean;
}

export interface StreamEvent {
  type: "status" | "sources" | "token" | "done" | "error";
  data: any;
  num_chunks?: number;
}

export interface UseStreamingQueryResult {
  sendStreamingQuery: (query: string) => Promise<void>;
  cancel: () => void;
  isStreaming: boolean;
  error: string | null;
  streamingAnswer: string;
  sources: Source[];
  status: string | null;
}
