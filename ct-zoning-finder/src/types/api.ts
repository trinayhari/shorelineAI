export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
}

export interface MunicipalitiesResponse {
  municipalities: Record<string, string | null>;
}

export interface ZoningSearchRequest {
  state: string;
  municipality: string;
}

export interface ZoningProcessRequest {
  state: string;
  municipality: string;
  pdfUrl: string;
  pdfTitle?: string;
}

export interface ZoningProcessResponse {
  jobId: string;
}

export interface ZoningStatusResponse {
  status: string;
  progress: number;
  error?: string;
  result?: {
    chunksCount: number;
    pdfUrl: string;
    pdfTitle: string;
  };
}

export interface ZoningQueryRequest {
  question: string;
  state: string;
  municipality: string;
}

export interface ZoningQueryResponse {
  answer: string;
}

export interface CacheCheckResponse {
  cached: boolean;
  chunksCount?: number;
}

export interface ParcelSearchRequest {
  query: string;
  town?: string;
  limit?: number;
}

export interface ParcelSearchResponse {
  answer: string;
}

export interface TownsResponse {
  towns: string[];
}
