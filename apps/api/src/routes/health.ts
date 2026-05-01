import type { FastifyInstance } from "fastify";
import type { AppDependencies } from "../app.js";

export function registerHealthRoute(app: FastifyInstance, dependencies: AppDependencies): void {
  app.get("/health", async () => {
    try {
      await dependencies.elasticsearch.ping();
      return {
        status: "ok",
        elasticsearch: {
          reachable: true,
          index: dependencies.config.productIndex,
        },
      };
    } catch {
      return {
        status: "degraded",
        elasticsearch: {
          reachable: false,
          index: dependencies.config.productIndex,
        },
      };
    }
  });
}