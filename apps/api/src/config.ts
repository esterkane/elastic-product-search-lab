import "dotenv/config";

export type ApiConfig = {
  elasticsearchUrl: string;
  elasticsearchUsername?: string;
  elasticsearchPassword?: string;
  elasticsearchUseAuth: boolean;
  productIndex: string;
  port: number;
};

export function loadConfig(env: NodeJS.ProcessEnv = process.env): ApiConfig {
  return {
    elasticsearchUrl: env.ELASTICSEARCH_URL ?? "http://localhost:9200",
    elasticsearchUsername: env.ELASTICSEARCH_USERNAME,
    elasticsearchPassword: env.ELASTICSEARCH_PASSWORD,
    elasticsearchUseAuth: ["1", "true", "yes"].includes((env.ELASTICSEARCH_USE_AUTH ?? "false").toLowerCase()),
    productIndex: env.PRODUCT_INDEX ?? "products-v1",
    port: Number(env.PORT ?? 3000),
  };
}