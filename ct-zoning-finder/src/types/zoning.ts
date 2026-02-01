export interface SearchResult {
  url: string;
  title: string;
  linkText?: string;
  isPdf: boolean;
  relevance?: number;
}

export interface ZoningSearchResponse {
  data: SearchResult[];
}

export interface ChunkDocument {
  _id?: string;
  chunkIndex: number;
  content: string;
  embedText?: string;
  embedding?: number[];
  sourceUrl: string;
  state?: string;
  municipality?: string;
  metadata?: Record<string, unknown>;
  createdAt?: Date;
  blocks?: unknown[];
}

export interface ProcessingJob {
  jobId: string;
  state: string;
  municipality: string;
  status: "pending" | "searching" | "selecting" | "downloading" | "parsing" | "embedding" | "complete" | "error";
  progress: number;
  error?: string;
  result?: {
    chunksCount: number;
    pdfUrl: string;
    pdfTitle: string;
  };
  createdAt: Date;
  updatedAt: Date;
}

export interface LLMSelectionResult {
  selectedIndex: number | null;
  confidence: "high" | "medium" | "low";
  reasoning: string;
}
