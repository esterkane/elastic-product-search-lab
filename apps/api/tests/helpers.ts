import { buildApp, type ElasticsearchLikeClient } from "../src/app.js";
import type { ApiConfig } from "../src/config.js";

export function testConfig(overrides: Partial<ApiConfig> = {}): ApiConfig {
  return {
    elasticsearchUrl: "http://localhost:9200",
    elasticsearchUseAuth: false,
    productIndex: "products-v1",
    port: 0,
    ...overrides,
  };
}

export function createMockClient(overrides: Partial<ElasticsearchLikeClient> = {}): ElasticsearchLikeClient {
  return {
    ping: async () => true,
    search: async () => ({ took: 1, hits: { total: { value: 0 }, hits: [] } }),
    get: async () => ({ _id: "P1", _source: {} }),
    ...overrides,
  };
}

export function buildTestApp(overrides: Partial<ElasticsearchLikeClient> = {}) {
  return buildApp({ config: testConfig(), elasticsearch: createMockClient(overrides) });
}