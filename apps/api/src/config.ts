import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { config as loadDotenv } from "dotenv";

for (const envPath of [resolve(process.cwd(), ".env"), resolve(process.cwd(), "..", "..", ".env")]) {
  if (existsSync(envPath)) {
    loadDotenv({ path: envPath, override: false });
  }
}

export type ApiConfig = {
  elasticsearchUrl: string;
  elasticsearchUsername?: string;
  elasticsearchPassword?: string;
  elasticsearchUseAuth: boolean;
  elasticsearchRequestTimeoutMs: number;
  productIndex: string;
  productLiveIndex?: string;
  productLiveOverlayEnabled: boolean;
  productSuggestIndex: string;
  port: number;
};

export function loadConfig(env: NodeJS.ProcessEnv = process.env): ApiConfig {
  return {
    elasticsearchUrl: env.ELASTICSEARCH_URL ?? "http://localhost:9200",
    elasticsearchUsername: env.ELASTICSEARCH_USERNAME,
    elasticsearchPassword: env.ELASTICSEARCH_PASSWORD,
    elasticsearchUseAuth: ["1", "true", "yes"].includes((env.ELASTICSEARCH_USE_AUTH ?? "false").toLowerCase()),
    elasticsearchRequestTimeoutMs: Number(env.ELASTICSEARCH_REQUEST_TIMEOUT_MS ?? 2000),
    productIndex: env.PRODUCT_INDEX ?? "products-read",
    productLiveIndex: env.PRODUCT_LIVE_INDEX,
    productLiveOverlayEnabled: ["1", "true", "yes"].includes((env.PRODUCT_LIVE_OVERLAY_ENABLED ?? "false").toLowerCase()),
    productSuggestIndex: env.PRODUCT_SUGGEST_INDEX ?? "product-suggest",
    port: Number(env.PORT ?? 3000),
  };
}
