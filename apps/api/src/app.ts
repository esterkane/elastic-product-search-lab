import Fastify, { type FastifyInstance } from "fastify";
import type { ApiConfig } from "./config.js";
import { registerHealthRoute } from "./routes/health.js";
import { registerMetricsRoute } from "./routes/metrics.js";
import { registerProductRoute } from "./routes/product.js";
import { registerSearchRoute } from "./routes/search.js";

export type ElasticsearchLikeClient = {
  ping: (...args: any[]) => Promise<unknown>;
  search: (...args: any[]) => Promise<any>;
  get: (...args: any[]) => Promise<any>;
};

export type AppDependencies = {
  config: ApiConfig;
  elasticsearch: ElasticsearchLikeClient;
};

export function buildApp(dependencies: AppDependencies): FastifyInstance {
  const app = Fastify({
    logger: process.env.NODE_ENV === "test" ? false : {
      redact: ["ELASTICSEARCH_PASSWORD", "elasticsearchPassword", "config.elasticsearchPassword", "req.headers.authorization"],
    },
    ajv: {
      customOptions: {
        coerceTypes: true,
        removeAdditional: "all",
      },
    },
  });

  app.decorate("dependencies", dependencies);

  registerHealthRoute(app, dependencies);
  registerSearchRoute(app, dependencies);
  registerProductRoute(app, dependencies);
  registerMetricsRoute(app);

  return app;
}