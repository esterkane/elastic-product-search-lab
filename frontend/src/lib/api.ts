export type Category = "relevance" | "ingestion" | "mapping" | "performance" | "resiliency";

export type SearchFilters = {
  repo?: string;
  path?: string;
  heading_path?: string;
  content_type?: string;
  license_family?: string;
};

export type SearchBoosts = {
  repo?: Record<string, number>;
  path?: Record<string, number>;
  heading_path?: Record<string, number>;
  content_type?: Record<string, number>;
  license_family?: Record<string, number>;
};

export type SearchHit = {
  id: string;
  score: number;
  title?: string | null;
  repo?: string | null;
  path?: string | null;
  heading_path?: string | null;
  content_type?: string | null;
  license_family?: string | null;
  source_url: string;
  score_breakdown?: {
    bm25: number;
    semantic: number;
    fusion: number;
    rerank?: number | null;
    final_rank: number;
    final_score: number;
  };
};

export type Source = {
  title: string;
  url: string;
};

export type RetrievalWarning = {
  code: string;
  message: string;
  stage: string;
};

export type Recommendation = {
  category: Category;
  recommendation: string;
  evidence: Source[];
};

export type SearchResponse = {
  hits: SearchHit[];
  recommendation_categories: Category[];
  warnings?: RetrievalWarning[];
  degraded?: boolean;
};

export type AnalyzeResponse = {
  query: string;
  recommendations: Recommendation[];
  warnings?: RetrievalWarning[];
  degraded?: boolean;
};

export type AnswerResponse = {
  answer: string;
  sources: Source[];
  warnings?: RetrievalWarning[];
  degraded?: boolean;
};

export type QueryRequest = {
  query: string;
  limit?: number;
  filters?: SearchFilters;
  boosts?: SearchBoosts;
  explain?: boolean;
};

export type IngestRepoRequest = {
  repo_url?: string;
  repo?: string;
  branch?: string;
  force?: boolean;
  update_sources?: boolean;
  max_files?: number;
};

export type IngestRepoResponse = {
  status: string;
  repo_url: string;
  branch?: string | null;
  message: string;
  repos_scanned: number;
  documents_scanned: number;
  chunks_indexed: number;
  new_chunks: number;
  updated_chunks: number;
  unchanged_chunks: number;
  errors: string[];
};

const JSON_HEADERS = { "Content-Type": "application/json" };

export async function search(request: QueryRequest): Promise<SearchResponse> {
  return postJson<SearchResponse>("/api/v1/search", request);
}

export async function analyze(request: QueryRequest): Promise<AnalyzeResponse> {
  return postJson<AnalyzeResponse>("/api/v1/analyze", request);
}

export async function answer(request: QueryRequest): Promise<AnswerResponse> {
  return postJson<AnswerResponse>("/api/v1/answer", request);
}

export async function ingestRepo(request: IngestRepoRequest): Promise<IngestRepoResponse> {
  return postJson<IngestRepoResponse>("/api/v1/ingest/repo", request);
}

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(body)
  });

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const message = payload?.error?.message ?? `Request failed with status ${response.status}`;
    throw new Error(message);
  }
  return payload as T;
}
