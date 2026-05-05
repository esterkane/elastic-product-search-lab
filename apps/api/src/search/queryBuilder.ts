import type { SearchQueryParams, SearchStrategy, SuggestQueryParams } from "./types.js";

type QueryDsl = Record<string, unknown>;

const BASELINE_FIELDS = ["title^4", "brand^2", "category^1.5", "description^0.8", "catalog_text^0.5"];
const ENRICHED_FIELDS = ["search_profile^3", "title^2", "category^1.5", "brand", "description^0.5", "catalog_text", "attributes"];
const DEFAULT_VECTOR_FIELD = "semantic_embedding";

export type RankingExtensionContext = {
  analyticsSignals?: Record<string, unknown>;
  cohortTags?: string[];
  merchandiserPolicies?: string[];
  policyFilters?: QueryDsl[];
  policyMustNot?: QueryDsl[];
  policyBoostFunctions?: QueryDsl[];
};

export type SearchDslDebug = {
  cohortBoosts: { tag: string; weight: number }[];
};

export type SearchDslBuildResult = {
  dsl: QueryDsl;
  requestedStrategy: SearchStrategy;
  executedStrategy: SearchStrategy | "hybrid_fallback";
  vectorProvided: boolean;
};

function textQuery(queryText?: string): QueryDsl {
  const trimmed = queryText?.trim();
  if (!trimmed) return { match_all: {} };

  return {
    multi_match: {
      query: trimmed,
      fields: BASELINE_FIELDS,
      type: "best_fields",
      operator: "and",
    },
  };
}

function buildFilters(params: SearchQueryParams, context: RankingExtensionContext = {}): QueryDsl[] {
  const filter: QueryDsl[] = [{ term: { is_deleted: false } }];

  if (params.category) filter.push({ term: { category: params.category.toLowerCase() } });
  if (params.brand) filter.push({ term: { brand: params.brand.toLowerCase() } });
  if (params.availability) filter.push({ term: { availability: params.availability } });

  if (params.minPrice !== undefined || params.maxPrice !== undefined) {
    const priceRange: Record<string, number> = {};
    if (params.minPrice !== undefined) priceRange.gte = params.minPrice;
    if (params.maxPrice !== undefined) priceRange.lte = params.maxPrice;
    filter.push({ range: { price: priceRange } });
  }

  return [...filter, ...(context.policyFilters ?? [])];
}

function exactMatchShouldClauses(queryText?: string): QueryDsl[] {
  const query = queryText?.trim();
  if (!query) return [];
  const lowerQuery = query.toLowerCase();
  return [
    { term: { "title.keyword": { value: lowerQuery, boost: 12 } } },
    { match_phrase: { title: { query, boost: 8 } } },
    { term: { brand: { value: lowerQuery, boost: 5 } } },
    { term: { category: { value: lowerQuery, boost: 3 } } },
  ];
}

export function buildBaselineBm25Query(params: SearchQueryParams, context: RankingExtensionContext = {}): QueryDsl {
  return {
    bool: {
      must: [textQuery(params.q)],
      filter: buildFilters(params, context),
      ...(context.policyMustNot?.length ? { must_not: context.policyMustNot } : {}),
    },
  };
}

export function buildEnrichedLexicalQuery(params: SearchQueryParams, context: RankingExtensionContext = {}): QueryDsl {
  const trimmed = params.q?.trim();
  const text = trimmed
    ? {
        multi_match: {
          query: trimmed,
          fields: ENRICHED_FIELDS,
          type: "best_fields",
          operator: "or",
          minimum_should_match: "2<70%",
          fuzziness: "AUTO",
        },
      }
    : { match_all: {} };
  return {
    bool: {
      must: [text],
      filter: buildFilters(params, context),
      should: exactMatchShouldClauses(trimmed),
      ...(context.policyMustNot?.length ? { must_not: context.policyMustNot } : {}),
    },
  };
}

export function buildBoostedRelevanceQuery(params: SearchQueryParams, context: RankingExtensionContext = {}): QueryDsl {
  const extensionFunctions = buildRankingExtensionFunctions(context);
  return {
    function_score: {
      query: buildBaselineBm25Query(params, context),
      score_mode: "sum",
      boost_mode: "sum",
      functions: [
        {
          field_value_factor: {
            field: "popularity_score",
            factor: 0.02,
            modifier: "sqrt",
            missing: 0,
          },
        },
        {
          gauss: {
            updated_at: {
              origin: "now",
              scale: "30d",
              offset: "7d",
              decay: 0.5,
            },
          },
          weight: 0.2,
        },
        ...extensionFunctions,
      ],
    },
  };
}

export function buildRankingExtensionFunctions(context: RankingExtensionContext): QueryDsl[] {
  const functions: QueryDsl[] = [];
  for (const tag of context.cohortTags ?? []) {
    functions.push({
      filter: { term: { cohort_tags: tag.toLowerCase() } },
      weight: 0.35,
    });
  }
  functions.push(...(context.policyBoostFunctions ?? []));
  return functions;
}

export function buildSearchDsl(params: SearchQueryParams, context: RankingExtensionContext = {}): QueryDsl {
  return buildSearchDslPlan(params, context).dsl;
}

export function buildSearchDslPlan(params: SearchQueryParams, context: RankingExtensionContext = {}): SearchDslBuildResult {
  const requestedStrategy = params.strategy ?? ((params.boost ?? true) ? "boosted_bm25" : "baseline_bm25");
  const vector = parseQueryVector(params.queryVector);
  const vectorProvided = vector.length > 0;
  const dsl = buildStrategyDsl(params, context, requestedStrategy, vector);
  return {
    dsl,
    requestedStrategy,
    executedStrategy: requestedStrategy === "hybrid_rrf" && !vectorProvided ? "hybrid_fallback" : requestedStrategy,
    vectorProvided,
  };
}

function buildStrategyDsl(
  params: SearchQueryParams,
  context: RankingExtensionContext,
  requestedStrategy: SearchStrategy,
  queryVector: number[],
): QueryDsl {
  if (requestedStrategy === "baseline_bm25") {
    return withDebug({ size: params.size, query: buildBaselineBm25Query(params, context), sort: ["_score"] }, params);
  }
  if (requestedStrategy === "boosted_bm25") {
    return withDebug({ size: params.size, query: buildBoostedRelevanceQuery(params, context), sort: ["_score"] }, params);
  }
  if (requestedStrategy === "hybrid_rrf" && queryVector.length > 0) {
    return withDebug(buildHybridRrfDsl(params, context, queryVector), params);
  }
  if (requestedStrategy === "reranked" && queryVector.length > 0) {
    return withDebug(buildHybridRrfDsl({ ...params, size: Math.max(params.size, 20) }, context, queryVector), params);
  }
  if (requestedStrategy === "reranked") {
    return withDebug({ size: Math.max(params.size, 20), query: buildEnrichedLexicalQuery(params, context), sort: ["_score"] }, params);
  }
  if (requestedStrategy === "enriched_lexical" || requestedStrategy === "hybrid_rrf") {
    return withDebug({ size: params.size, query: buildEnrichedLexicalQuery(params, context), sort: ["_score"] }, params);
  }

  const useBoosts = params.boost ?? true;
  const query = useBoosts ? buildBoostedRelevanceQuery(params, context) : buildBaselineBm25Query(params, context);
  return withDebug({ size: params.size, query, sort: ["_score"] }, params);
}

function buildHybridRrfDsl(params: SearchQueryParams, context: RankingExtensionContext, queryVector: number[]): QueryDsl {
  const filters = buildFilters(params, context);
  return {
    size: params.size,
    retriever: {
      rrf: {
        retrievers: [
          {
            standard: {
              query: buildEnrichedLexicalQuery(params, context),
            },
          },
          {
            knn: {
              field: params.vectorField || DEFAULT_VECTOR_FIELD,
              query_vector: queryVector,
              k: Math.max(params.size, 20),
              num_candidates: Math.max(params.size * 10, 100),
              filter: { bool: { filter: filters } },
            },
          },
        ],
        rank_constant: 60,
        rank_window_size: Math.max(params.size, 50),
      },
    },
  };
}

function withDebug(dsl: QueryDsl, params: SearchQueryParams): QueryDsl {
  return {
    ...dsl,
    ...(params.debug ? { explain: true, profile: true } : {}),
  };
}

export function parseQueryVector(raw?: string): number[] {
  if (!raw) return [];
  const vector = raw.split(",").map((value) => Number(value.trim()));
  return vector.every((value) => Number.isFinite(value)) ? vector : [];
}

export function buildSearchDslDebug(context: RankingExtensionContext = {}): SearchDslDebug {
  return {
    cohortBoosts: (context.cohortTags ?? []).map((tag) => ({ tag: tag.toLowerCase(), weight: 0.35 })),
  };
}

export function buildSuggestDsl(params: SuggestQueryParams): QueryDsl {
  const query = params.q.trim();
  return {
    size: params.size,
    query: {
      multi_match: {
        query,
        type: "bool_prefix",
        fields: ["suggest_text", "suggest_text._2gram", "suggest_text._3gram", "title^2", "brand", "category"],
      },
    },
    _source: ["product_id", "title", "brand", "category", "suggest_text"],
  };
}
