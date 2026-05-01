export type Category = "relevance" | "ingestion" | "mapping" | "performance" | "resiliency";

export type SearchFilters = {
  repo?: string;
  content_type?: string;
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

export type Recommendation = {
  category: Category;
  recommendation: string;
  evidence: Source[];
};

export type SearchResponse = {
  hits: SearchHit[];
  recommendation_categories: Category[];
};

export type AnalyzeResponse = {
  query: string;
  recommendations: Recommendation[];
};

export type AnswerResponse = {
  answer: string;
  sources: Source[];
};

export type QueryRequest = {
  query: string;
  limit?: number;
  filters?: SearchFilters;
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
