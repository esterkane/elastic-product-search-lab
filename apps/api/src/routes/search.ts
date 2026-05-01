import type { FastifyInstance } from "fastify";
import type { AppDependencies } from "../app.js";
import { searchProducts } from "../search/searchClient.js";
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
    boost: { type: "boolean", default: true },
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

      return searchProducts(dependencies.elasticsearch, dependencies.config.productIndex, params);
    }
  );
}