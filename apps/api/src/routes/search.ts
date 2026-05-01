import type { FastifyInstance } from "fastify";
import type { AppDependencies } from "../app.js";
import { normalizeProductHit } from "../search/normalize.js";
import { buildSearchDsl } from "../search/queryBuilder.js";
import type { SearchQueryParams } from "../search/types.js";

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
  },
} as const;

function totalHitsValue(total: unknown): number {
  if (typeof total === "number") return total;
  if (total && typeof total === "object" && "value" in total) {
    return Number((total as { value: unknown }).value);
  }
  return 0;
}

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

      const dsl = buildSearchDsl(params);
      const response = await dependencies.elasticsearch.search({
        index: dependencies.config.productIndex,
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
  );
}