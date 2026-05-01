import type { SearchQueryParams } from "./types.js";

type QueryDsl = Record<string, unknown>;

export function buildSearchDsl(params: SearchQueryParams): QueryDsl {
  const must: QueryDsl[] = [];
  const filter: QueryDsl[] = [];

  const queryText = params.q?.trim();
  if (queryText) {
    must.push({
      multi_match: {
        query: queryText,
        fields: ["title^3", "brand^2", "category^1.5", "description", "catalog_text"],
        type: "best_fields",
        operator: "and",
      },
    });
  } else {
    must.push({ match_all: {} });
  }

  if (params.category) {
    filter.push({ term: { category: params.category.toLowerCase() } });
  }
  if (params.brand) {
    filter.push({ term: { brand: params.brand.toLowerCase() } });
  }
  if (params.availability) {
    filter.push({ term: { availability: params.availability } });
  }
  if (params.minPrice !== undefined || params.maxPrice !== undefined) {
    const priceRange: Record<string, number> = {};
    if (params.minPrice !== undefined) priceRange.gte = params.minPrice;
    if (params.maxPrice !== undefined) priceRange.lte = params.maxPrice;
    filter.push({ range: { price: priceRange } });
  }

  return {
    size: params.size,
    query: {
      bool: {
        must,
        filter,
      },
    },
    sort: ["_score"],
  };
}