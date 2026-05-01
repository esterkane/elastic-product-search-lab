import type { FastifyInstance } from "fastify";

export function registerMetricsRoute(app: FastifyInstance): void {
  app.get("/metrics/search-latency-demo", async () => ({
    p50: null,
    p95: null,
    p99: null,
    errorRate: null,
    timeoutRate: null,
  }));
}