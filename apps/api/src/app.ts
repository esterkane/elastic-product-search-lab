import Fastify, { type FastifyError, type FastifyInstance, type FastifyReply, type FastifyRequest } from "fastify";
import type { ApiConfig } from "./config.js";
import { registerHealthRoute } from "./routes/health.js";
import { registerMetricsRoute } from "./routes/metrics.js";
import { registerProductRoute } from "./routes/product.js";
import { registerSearchRoute } from "./routes/search.js";

export type ElasticsearchLikeClient = {
  ping: (...args: any[]) => Promise<unknown>;
  search: (...args: any[]) => Promise<any>;
  get: (...args: any[]) => Promise<any>;
  mget?: (...args: any[]) => Promise<any>;
};

export type AppDependencies = {
  config: ApiConfig;
  elasticsearch: ElasticsearchLikeClient;
};

function isElasticsearchError(error: FastifyError): boolean {
  const maybeError = error as FastifyError & { meta?: { statusCode?: number }; code?: string };
  return Boolean(maybeError.meta?.statusCode || maybeError.code?.startsWith("UND_ERR") || maybeError.code === "TimeoutError");
}

function sendSafeError(error: FastifyError, request: FastifyRequest, reply: FastifyReply) {
  const statusCode = error.statusCode ?? 500;

  if (statusCode < 500) {
    return reply.code(statusCode).send({
      error: statusCode === 400 ? "Bad Request" : "Request Error",
      message: error.message,
    });
  }

  request.log.error({ err: error, route: request.routeOptions.url }, "request failed");
  const serviceUnavailable = isElasticsearchError(error);
  return reply.code(serviceUnavailable ? 503 : 500).send({
    error: serviceUnavailable ? "Service Unavailable" : "Internal Server Error",
    message: serviceUnavailable ? "Search backend is temporarily unavailable" : "Unexpected server error",
  });
}

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

  app.addHook("onResponse", async (request, reply) => {
    request.log.info(
      {
        method: request.method,
        url: request.url,
        statusCode: reply.statusCode,
        responseTimeMs: reply.elapsedTime,
      },
      "request completed",
    );
  });

  app.setErrorHandler(sendSafeError);

  registerHealthRoute(app, dependencies);
  registerSearchRoute(app, dependencies);
  registerProductRoute(app, dependencies);
  registerMetricsRoute(app);

  return app;
}
