import { buildApp, type ElasticsearchLikeClient } from "../src/app.js";
import type { ApiConfig } from "../src/config.js";

export function testConfig(overrides: Partial<ApiConfig> = {}): ApiConfig {
  return {
    elasticsearchUrl: "http://localhost:9200",
    elasticsearchUseAuth: false,
    productIndex: "products-read",
    productLiveOverlayEnabled: false,
    productSuggestIndex: "product-suggest",
    port: 0,
    ...overrides,
  };
}

export function createMockClient(overrides: Partial<ElasticsearchLikeClient> = {}): ElasticsearchLikeClient {
  return {
    ping: async () => true,
    search: async () => ({ took: 1, hits: { total: { value: 0 }, hits: [] } }),
    get: async () => ({ _id: "P1", _source: {} }),
    mget: async () => ({ docs: [] }),
    ...overrides,
  };
}

export function buildTestApp(overrides: Partial<ElasticsearchLikeClient> = {}, configOverrides: Partial<ApiConfig> = {}) {
  return buildApp({ config: testConfig(configOverrides), elasticsearch: createMockClient(overrides) });
}
