import { afterEach, describe, expect, it } from "vitest";
import { buildTestApp } from "./helpers.js";

let app: ReturnType<typeof buildTestApp> | undefined;

afterEach(async () => {
  await app?.close();
  app = undefined;
});

describe("GET /health", () => {
  it("returns ok when Elasticsearch ping succeeds", async () => {
    app = buildTestApp({ ping: async () => true });

    const response = await app.inject({ method: "GET", url: "/health" });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toEqual({
      status: "ok",
      elasticsearch: { reachable: true, index: "products-v1" },
    });
  });

  it("returns degraded when Elasticsearch ping fails", async () => {
    app = buildTestApp({ ping: async () => { throw new Error("down"); } });

    const response = await app.inject({ method: "GET", url: "/health" });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toEqual({
      status: "degraded",
      elasticsearch: { reachable: false, index: "products-v1" },
    });
  });
});