import { Client } from "@elastic/elasticsearch";
import type { ApiConfig } from "./config.js";

export function createElasticsearchClient(config: ApiConfig): Client {
  const options: ConstructorParameters<typeof Client>[0] = {
    node: config.elasticsearchUrl,
  };

  if (config.elasticsearchUseAuth && config.elasticsearchUsername && config.elasticsearchPassword) {
    options.auth = {
      username: config.elasticsearchUsername,
      password: config.elasticsearchPassword,
    };
  }

  return new Client(options);
}