import type { SearchQueryParams, SuggestQueryParams } from "./types.js";

type QueryDsl = Record<string, unknown>;

const BASELINE_FIELDS = ["title^4", "brand^2", "category^1.5", "description^0.8", "catalog_text^0.5"];

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

export function buildBaselineBm25Query(params: SearchQueryParams, context: RankingExtensionContext = {}): QueryDsl {
  return {
    bool: {
      must: [textQuery(params.q)],
      filter: buildFilters(params, context),
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
  const useBoosts = params.boost ?? true;
  const query = useBoosts ? buildBoostedRelevanceQuery(params, context) : buildBaselineBm25Query(params, context);

  return {
    size: params.size,
    query,
    sort: ["_score"],
    ...(params.debug ? { explain: true, profile: true } : {}),
  };
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
