import type { FastifyInstance } from "fastify";
import type { AppDependencies } from "../app.js";
import { loadPoliciesFromFile } from "../search/policies.js";
import { searchProducts, suggestProducts } from "../search/searchClient.js";
import type { SearchQueryParams, SuggestQueryParams } from "../search/types.js";

const searchQuerySchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    q: { type: "string", minLength: 1 },
    category: { type: "string", minLength: 1 },
    brand: { type: "string", minLength: 1 },
    availability: { type: "string", minLength: 1 },
    minPrice: { type: "number", minimum: 0 },
    maxPrice: { type: "number", minimum: 0 },
    size: { type: "integer", minimum: 1, maximum: 50, default: 10 },
    debug: { type: "boolean", default: false },
    boost: { type: "boolean", default: true },
    cohorts: { type: "string", minLength: 1 },
    strategy: { type: "string", enum: ["baseline_bm25", "boosted_bm25", "enriched_lexical", "hybrid_rrf", "reranked"] },
    queryVector: { type: "string", minLength: 1 },
    vectorField: { type: "string", minLength: 1, default: "semantic_embedding" },
    rerank: { type: "boolean", default: false },
  },
} as const;

const suggestQuerySchema = {
  type: "object",
  additionalProperties: false,
  required: ["q"],
  properties: {
    q: { type: "string", minLength: 1 },
    size: { type: "integer", minimum: 1, maximum: 20, default: 5 },
    debug: { type: "boolean", default: false },
  },
} as const;

export function registerSearchRoute(app: FastifyInstance, dependencies: AppDependencies): void {
  app.get<{ Querystring: SearchQueryParams }>(
    "/search",
    { schema: { querystring: searchQuerySchema } },
    async (request, reply) => {
      const params = request.query;
      if (params.minPrice !== undefined && params.maxPrice !== undefined && params.minPrice > params.maxPrice) {
        return reply.code(400).send({
          error: "Bad Request",
          message: "minPrice must be less than or equal to maxPrice",
        });
      }

      return searchProducts(dependencies.elasticsearch, dependencies.config.productIndex, params, {
        enabled: dependencies.config.productLiveOverlayEnabled,
        index: dependencies.config.productLiveIndex,
      }, loadPoliciesFromFile(dependencies.config.searchPolicyPath));
    }
  );

  app.get<{ Querystring: SuggestQueryParams & { debug?: boolean } }>(
    "/suggest",
    { schema: { querystring: suggestQuerySchema } },
    async (request) => {
      return suggestProducts(
        dependencies.elasticsearch,
        dependencies.config.productSuggestIndex,
        { q: request.query.q, size: request.query.size },
        request.query.debug ?? false,
      );
    },
  );
}
