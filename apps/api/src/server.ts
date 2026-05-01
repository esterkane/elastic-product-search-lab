import { buildApp } from "./app.js";
import { loadConfig } from "./config.js";
import { createElasticsearchClient } from "./elasticsearch.js";

const config = loadConfig();
const app = buildApp({
  config,
  elasticsearch: createElasticsearchClient(config),
});

try {
  await app.listen({ host: "0.0.0.0", port: config.port });
} catch (error) {
  app.log.error({ error }, "API startup failed");
  process.exit(1);
}