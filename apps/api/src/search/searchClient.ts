import type { ElasticsearchLikeClient } from "../app.js";
import { normalizeProductHit } from "./normalize.js";
import { mergeVolatileOverlay, type OverlayOptions } from "./overlay.js";
import { evaluateSearchPolicies, type SearchPolicy } from "./policies.js";
import { buildSearchDslDebug, buildSearchDslPlan, buildSuggestDsl, type RankingExtensionContext } from "./queryBuilder.js";
import type { ProductSearchResponse, ProductSuggestOption, ProductSuggestResponse, SearchQueryParams, SuggestQueryParams } from "./types.js";

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
  params: SearchQueryParams,
  overlayOptions: OverlayOptions = { enabled: false },
  policies: SearchPolicy[] = [],
): Promise<ProductSearchResponse> {
  const cohorts = parseCohorts(params.cohorts);
  const policyEvaluation = evaluateSearchPolicies(policies, params.q);
  const effectiveParams = { ...params, q: policyEvaluation.queryText ?? params.q };
  const rankingContext: RankingExtensionContext = {
    cohortTags: cohorts,
    policyFilters: policyEvaluation.filters,
    policyMustNot: policyEvaluation.mustNot,
    policyBoostFunctions: policyEvaluation.boostFunctions,
    merchandiserPolicies: policyEvaluation.firedPolicies.map((policy) => policy.id),
  };
  const plan = buildSearchDslPlan(effectiveParams, rankingContext);
  const startedAt = performance.now();
  const response = await client.search({
    index: indexName,
    ...plan.dsl,
  });
  const latencyMs = performance.now() - startedAt;
  const hits = response.hits?.hits ?? [];
  const products = maybeRerankProducts(effectiveParams.q, hits.map(normalizeProductHit), Boolean(params.rerank || params.strategy === "reranked"))
    .slice(0, params.size);
  const overlay = await mergeVolatileOverlay(client, products, overlayOptions);

  return {
    took: response.took ?? 0,
    total: totalHitsValue(response.hits?.total),
    products: overlay.products,
    ...(params.debug ? {
      debug: {
        query: plan.dsl,
        overlay: overlay.debug,
        policies: {
          fired: policyEvaluation.firedPolicies,
          routingHints: policyEvaluation.routingHints,
        },
        cohorts: {
          requested: cohorts,
          boosts: buildSearchDslDebug(rankingContext).cohortBoosts,
        },
        strategy: {
          requested: plan.requestedStrategy,
          executed: plan.executedStrategy,
          vectorProvided: plan.vectorProvided,
          reranked: Boolean(params.rerank || params.strategy === "reranked"),
          latencyMs,
        },
        profile: response.profile,
        explanations: hits.map((hit: { _explanation?: unknown }) => hit._explanation).filter(Boolean),
      },
    } : {}),
  };
}

function parseCohorts(value?: string): string[] {
  return [...new Set((value ?? "")
    .split(",")
    .map((tag) => tag.trim().toLowerCase())
    .filter(Boolean))];
}

function maybeRerankProducts(query: string | undefined, products: ReturnType<typeof normalizeProductHit>[], enabled: boolean) {
  const terms = (query ?? "").toLowerCase().split(/\s+/).filter(Boolean);
  if (!enabled || terms.length === 0) return products;
  return products
    .map((product, position) => {
      const text = [product.title, product.brand, product.category, product.description, JSON.stringify(product.attributes)]
        .join(" ")
        .toLowerCase();
      const overlap = terms.filter((term) => text.includes(term)).length;
      const exactTitle = product.title.toLowerCase() === terms.join(" ") ? 10 : 0;
      return { product, position, rerankScore: exactTitle + overlap + Number(product.score ?? 0) * 0.001 };
    })
    .sort((left, right) => right.rerankScore - left.rerankScore || left.position - right.position)
    .map((row) => ({ ...row.product, score: row.rerankScore }));
}

function normalizeSuggestHit(hit: { _id?: string; _score?: number; _source?: Record<string, unknown> }): ProductSuggestOption {
  const source = hit._source ?? {};
  const title = String(source.title ?? source.suggest_text ?? "");
  return {
    productId: String(source.product_id ?? hit._id ?? ""),
    text: String(source.suggest_text ?? title),
    title,
    brand: String(source.brand ?? ""),
    category: String(source.category ?? ""),
    score: hit._score,
  };
}

export async function suggestProducts(
  client: ElasticsearchLikeClient,
  indexName: string,
  params: SuggestQueryParams,
  debug = false,
): Promise<ProductSuggestResponse> {
  const dsl = buildSuggestDsl(params);
  const response = await client.search({
    index: indexName,
    ...dsl,
  });
  const hits = response.hits?.hits ?? [];
  return {
    took: response.took ?? 0,
    suggestions: hits.map(normalizeSuggestHit),
    ...(debug ? { debug: { query: dsl } } : {}),
  };
}
