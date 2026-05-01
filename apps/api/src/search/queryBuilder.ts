import type { SearchQueryParams } from "./types.js";

type QueryDsl = Record<string, unknown>;

const BASELINE_FIELDS = ["title^4", "brand^2", "category^1.5", "description^0.8", "catalog_text^0.5"];

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

function buildFilters(params: SearchQueryParams): QueryDsl[] {
  const filter: QueryDsl[] = [];

  if (params.category) filter.push({ term: { category: params.category.toLowerCase() } });
  if (params.brand) filter.push({ term: { brand: params.brand.toLowerCase() } });
  if (params.availability) filter.push({ term: { availability: params.availability } });

  if (params.minPrice !== undefined || params.maxPrice !== undefined) {
    const priceRange: Record<string, number> = {};
    if (params.minPrice !== undefined) priceRange.gte = params.minPrice;
    if (params.maxPrice !== undefined) priceRange.lte = params.maxPrice;
    filter.push({ range: { price: priceRange } });
  }

  return filter;
}

export function buildBaselineBm25Query(params: SearchQueryParams): QueryDsl {
  return {
    bool: {
      must: [textQuery(params.q)],
      filter: buildFilters(params),
    },
  };
}

export function buildBoostedRelevanceQuery(params: SearchQueryParams): QueryDsl {
  return {
    function_score: {
      query: buildBaselineBm25Query(params),
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
      ],
    },
  };
}

export function buildSearchDsl(params: SearchQueryParams): QueryDsl {
  const useBoosts = params.boost ?? true;
  const query = useBoosts ? buildBoostedRelevanceQuery(params) : buildBaselineBm25Query(params);

  return {
    size: params.size,
    query,
    sort: ["_score"],
    ...(params.debug ? { explain: true, profile: true } : {}),
  };
}