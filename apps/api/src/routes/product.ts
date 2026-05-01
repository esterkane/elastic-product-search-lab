import type { FastifyInstance } from "fastify";
import type { AppDependencies } from "../app.js";
import { normalizeProductHit } from "../search/normalize.js";

export function registerProductRoute(app: FastifyInstance, dependencies: AppDependencies): void {
  app.get<{ Params: { id: string } }>(
    "/product/:id",
    {
      schema: {
        params: {
          type: "object",
          required: ["id"],
          properties: {
            id: { type: "string", minLength: 1 },
          },
        },
      },
    },
    async (request, reply) => {
      try {
        const response = await dependencies.elasticsearch.get({
          index: dependencies.config.productIndex,
          id: request.params.id,
        });
        return normalizeProductHit(response);
      } catch (error: any) {
        if (error?.statusCode === 404 || error?.meta?.statusCode === 404) {
          return reply.code(404).send({ error: "Not Found", message: "Product not found" });
        }
        throw error;
      }
    }
  );
}