export type SearchStrategy = "baseline_bm25" | "boosted_bm25" | "enriched_lexical" | "hybrid_rrf" | "reranked";

export type SearchQueryParams = {
  q?: string;
  category?: string;
  brand?: string;
  availability?: string;
  minPrice?: number;
  maxPrice?: number;
  size: number;
  debug: boolean;
  boost?: boolean;
  cohorts?: string;
  strategy?: SearchStrategy;
  queryVector?: string;
  vectorField?: string;
  rerank?: boolean;
  vectorDims?: number;
};

export type SuggestQueryParams = {
  q: string;
  size: number;
};

export type ProductResponse = {
  productId: string;
  title: string;
  description: string;
  brand: string;
  category: string;
  attributes: Record<string, unknown>;
  price: number;
  currency: string;
  availability: string;
  popularityScore: number;
  sellerId: string;
  updatedAt: string;
  score?: number;
  overlay?: {
    source: string;
    appliedFields: string[];
  };
};

export type ProductSearchResponse = {
  took: number;
  total: number;
  products: ProductResponse[];
  debug?: {
    query: Record<string, unknown>;
    overlay?: {
      enabled: boolean;
      index?: string;
      attempted: boolean;
      applied: number;
      error?: string;
    };
    policies?: {
      fired: Array<{
        id: string;
        type: string;
        priority: number;
        reason?: string;
        actions: string[];
      }>;
      routingHints: string[];
    };
    cohorts?: {
      requested: string[];
      boosts: Array<{ tag: string; weight: number }>;
    };
    strategy?: {
      requested: SearchStrategy;
      executed: SearchStrategy;
      vectorProvided: boolean;
      vectorGenerated: boolean;
      vectorDims: number;
      reranked: boolean;
      latencyMs: number;
    };
    profile?: unknown;
    explanations?: unknown[];
  };
};

export type ProductSuggestOption = {
  productId: string;
  text: string;
  title: string;
  brand: string;
  category: string;
  score?: number;
};

export type ProductSuggestResponse = {
  took: number;
  suggestions: ProductSuggestOption[];
  debug?: {
    query: Record<string, unknown>;
  };
};
