import type { ElasticsearchLikeClient } from "../app.js";
import { normalizeProductHit } from "./normalize.js";
import { buildSearchDsl } from "./queryBuilder.js";
import type { ProductSearchResponse, SearchQueryParams } from "./types.js";

function totalHitsValue(total: unknown): number {
  if (typeof total === "number") return total;
  if (total && typeof total === "object" && "value" in total) {
    return Number((total as { value: unknown }).value);
  }
  return 0;
}

export async function searchProducts(
  client: ElasticsearchLikeClient,
  indexName: string,
  params: SearchQueryParams
): Promise<ProductSearchResponse> {
  const dsl = buildSearchDsl(params);
  const response = await client.search({
    index: indexName,
    ...dsl,
  });
  const hits = response.hits?.hits ?? [];

  return {
    took: response.took ?? 0,
    total: totalHitsValue(response.hits?.total),
    products: hits.map(normalizeProductHit),
    ...(params.debug ? { debug: { query: dsl } } : {}),
  };
}