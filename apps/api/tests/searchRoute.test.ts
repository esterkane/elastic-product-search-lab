import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { buildTestApp } from "./helpers.js";

let app: ReturnType<typeof buildTestApp> | undefined;

afterEach(async () => {
  await app?.close();
  app = undefined;
});

describe("GET /search", () => {
  it("uses products-read as the stable retrieval alias by default", async () => {
    let requestedIndex = "";
    app = buildTestApp({
      search: async (request) => {
        requestedIndex = request.index;
        return { took: 1, hits: { total: { value: 0 }, hits: [] } };
      },
    });

    const response = await app.inject({ method: "GET", url: "/search?q=mouse" });

    expect(response.statusCode).toBe(200);
    expect(requestedIndex).toBe("products-read");
  });

  it("rejects invalid size", async () => {
    app = buildTestApp();

    const response = await app.inject({ method: "GET", url: "/search?size=0" });

    expect(response.statusCode).toBe(400);
  });

  it("rejects inverted price ranges", async () => {
    app = buildTestApp();

    const response = await app.inject({ method: "GET", url: "/search?minPrice=200&maxPrice=100" });

    expect(response.statusCode).toBe(400);
    expect(response.json().message).toBe("minPrice must be less than or equal to maxPrice");
  });

  it("includes debug query DSL when requested", async () => {
    app = buildTestApp({
      search: async () => ({
        took: 3,
        hits: {
          total: { value: 1 },
          hits: [
            {
              _id: "P100002",
              _score: 4.2,
              _source: {
                product_id: "P100002",
                title: "Sony Headphones",
                description: "Noise canceling headphones",
                brand: "Sony",
                category: "Electronics > Headphones",
                attributes: {},
                price: 149.99,
                currency: "USD",
                availability: "in_stock",
                popularity_score: 98.7,
                seller_id: "seller-audio-014",
                updated_at: "2026-04-18T08:00:00Z",
              },
            },
          ],
        },
      }),
    });

    const response = await app.inject({ method: "GET", url: "/search?q=headphones&debug=true" });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      took: 3,
      total: 1,
      products: [{ productId: "P100002", title: "Sony Headphones" }],
      debug: { query: { size: 10 } },
    });
  });

  it("optionally merges volatile price and inventory overlays", async () => {
    app = buildTestApp(
      {
        search: async () => ({
          took: 3,
          hits: {
            total: { value: 1 },
            hits: [
              {
                _id: "P100002",
                _score: 4.2,
                _source: {
                  product_id: "P100002",
                  title: "Sony Headphones",
                  description: "Noise canceling headphones",
                  brand: "Sony",
                  category: "Electronics > Headphones",
                  attributes: {},
                  price: 149.99,
                  currency: "USD",
                  availability: "in_stock",
                  popularity_score: 98.7,
                  seller_id: "seller-audio-014",
                  updated_at: "2026-04-18T08:00:00Z",
                },
              },
            ],
          },
        }),
        mget: async () => ({
          docs: [
            {
              _id: "P100002",
              found: true,
              _source: { price: 139.99, currency: "USD", availability: "limited_stock" },
            },
          ],
        }),
      },
      { productLiveOverlayEnabled: true, productLiveIndex: "products-live" },
    );

    const response = await app.inject({ method: "GET", url: "/search?q=headphones&debug=true" });

    expect(response.statusCode).toBe(200);
    expect(response.json().products[0]).toMatchObject({
      productId: "P100002",
      price: 139.99,
      availability: "limited_stock",
      overlay: { source: "products-live", appliedFields: ["price", "currency", "availability"] },
    });
    expect(response.json().debug.overlay).toMatchObject({ enabled: true, index: "products-live", attempted: true, applied: 1 });
  });

  it("keeps search responses stable when overlay is disabled", async () => {
    let mgetCalled = false;
    app = buildTestApp({
      search: async () => ({
        took: 1,
        hits: {
          total: { value: 1 },
          hits: [{ _id: "P1", _source: { product_id: "P1", title: "Mouse", price: 10, availability: "in_stock" } }],
        },
      }),
      mget: async () => {
        mgetCalled = true;
        return { docs: [] };
      },
    });

    const response = await app.inject({ method: "GET", url: "/search?q=mouse&debug=true" });

    expect(response.statusCode).toBe(200);
    expect(mgetCalled).toBe(false);
    expect(response.json().products[0]).toMatchObject({ productId: "P1", price: 10, availability: "in_stock" });
  });

  it("returns suggestions from the separate suggest index", async () => {
    let requestedIndex = "";
    app = buildTestApp({
      search: async (request) => {
        requestedIndex = request.index;
        return {
          took: 2,
          hits: {
            total: { value: 1 },
            hits: [
              {
                _id: "P1",
                _score: 3,
                _source: {
                  product_id: "P1",
                  suggest_text: "Wireless Mouse Contoso Accessories",
                  title: "Wireless Mouse",
                  brand: "Contoso",
                  category: "Accessories",
                },
              },
            ],
          },
        };
      },
    });

    const response = await app.inject({ method: "GET", url: "/suggest?q=wir&size=5" });

    expect(response.statusCode).toBe(200);
    expect(requestedIndex).toBe("product-suggest");
    expect(response.json()).toMatchObject({
      took: 2,
      suggestions: [{ productId: "P1", text: "Wireless Mouse Contoso Accessories", title: "Wireless Mouse" }],
    });
  });

  it("executes hybrid RRF retrieval and exposes profile details in debug mode", async () => {
    let capturedRequest: any;
    app = buildTestApp({
      search: async (request) => {
        capturedRequest = request;
        return {
          took: 7,
          profile: { shards: [{ id: "0", searches: [] }] },
          hits: {
            total: { value: 1 },
            hits: [
              {
                _id: "P1",
                _score: 3,
                _explanation: { value: 3, description: "rrf score" },
                _source: {
                  product_id: "P1",
                  title: "Travel Headphones",
                  description: "Quiet wireless headphones",
                  brand: "Contoso",
                  category: "Audio",
                  attributes: {},
                  price: 99,
                  currency: "EUR",
                  availability: "in_stock",
                  popularity_score: 9,
                  seller_id: "seller-1",
                  updated_at: "2026-05-01T00:00:00Z",
                },
              },
            ],
          },
        };
      },
    });

    const response = await app.inject({
      method: "GET",
      url: "/search?q=quiet%20travel%20headphones&strategy=hybrid_rrf&queryVector=0.1,0.2,0.3&debug=true",
    });

    expect(response.statusCode).toBe(200);
    expect(capturedRequest.retriever.rrf.retrievers[1].knn.query_vector).toEqual([0.1, 0.2, 0.3]);
    expect(response.json().debug.strategy).toMatchObject({
      requested: "hybrid_rrf",
      executed: "hybrid_rrf",
      vectorProvided: true,
      vectorGenerated: false,
      vectorDims: 3,
      reranked: false,
    });
    expect(response.json().debug.profile).toEqual({ shards: [{ id: "0", searches: [] }] });
    expect(response.json().debug.explanations).toEqual([{ value: 3, description: "rrf score" }]);
  });

  it("generates a query vector for hybrid search when the caller omits one", async () => {
    let capturedRequest: any;
    app = buildTestApp({
      search: async (request) => {
        capturedRequest = request;
        return { took: 2, hits: { total: { value: 0 }, hits: [] } };
      },
    });

    const response = await app.inject({ method: "GET", url: "/search?q=quiet%20headphones&strategy=hybrid_rrf&vectorDims=4&debug=true" });

    expect(response.statusCode).toBe(200);
    expect(capturedRequest.retriever.rrf.retrievers[1].knn.query_vector).toHaveLength(4);
    expect(response.json().debug.strategy).toMatchObject({
      requested: "hybrid_rrf",
      executed: "hybrid_rrf",
      vectorProvided: false,
      vectorGenerated: true,
      vectorDims: 4,
    });
  });

  it("can rerank first-stage candidates deterministically", async () => {
    app = buildTestApp({
      search: async () => ({
        took: 4,
        hits: {
          total: { value: 2 },
          hits: [
            {
              _id: "P2",
              _score: 10,
              _source: { product_id: "P2", title: "Generic Audio Case", description: "", brand: "", category: "", attributes: {}, price: 1, availability: "in_stock" },
            },
            {
              _id: "P1",
              _score: 1,
              _source: { product_id: "P1", title: "quiet travel headphones", description: "", brand: "", category: "", attributes: {}, price: 2, availability: "in_stock" },
            },
          ],
        },
      }),
    });

    const response = await app.inject({ method: "GET", url: "/search?q=quiet%20travel%20headphones&strategy=reranked&rerank=true&debug=true" });

    expect(response.statusCode).toBe(200);
    expect(response.json().products[0].productId).toBe("P1");
    expect(response.json().debug.strategy.reranked).toBe(true);
  });

  it("shows fired policies and cohort boosts in debug output", async () => {
    const policyDir = mkdtempSync(join(tmpdir(), "policy-test-"));
    const policyPath = join(policyDir, "policies.json");
    writeFileSync(policyPath, JSON.stringify({
      policies: [
        {
          id: "pin-mouse",
          enabled: true,
          type: "pin_boost",
          priority: 10,
          queryMatch: "mouse",
          productIds: ["P1"],
          boost: 2,
          reason: "Promote mouse fixture",
        },
      ],
    }));
    let capturedQuery: any;
    app = buildTestApp(
      {
        search: async (request) => {
          capturedQuery = request.query;
          return {
            took: 1,
            hits: {
              total: { value: 1 },
              hits: [{ _id: "P1", _source: { product_id: "P1", title: "Mouse", price: 10, availability: "in_stock" } }],
            },
          };
        },
      },
      { searchPolicyPath: policyPath },
    );

    const response = await app.inject({ method: "GET", url: "/search?q=mouse&cohorts=student&debug=true" });

    expect(response.statusCode).toBe(200);
    expect(capturedQuery.function_score.functions).toEqual(expect.arrayContaining([
      { filter: { term: { cohort_tags: "student" } }, weight: 0.35 },
      { filter: { ids: { values: ["P1"] } }, weight: 2 },
    ]));
    expect(response.json().debug).toMatchObject({
      policies: {
        fired: [{ id: "pin-mouse", type: "pin_boost", priority: 10, actions: ["boost_products"] }],
      },
      cohorts: {
        requested: ["student"],
        boosts: [{ tag: "student", weight: 0.35 }],
      },
    });
  });

  it("returns a sanitized backend error shape", async () => {
    const error = Object.assign(new Error("connect ETIMEDOUT including internal host details"), {
      code: "UND_ERR_CONNECT_TIMEOUT",
    });
    app = buildTestApp({ search: async () => Promise.reject(error) });

    const response = await app.inject({ method: "GET", url: "/search?q=headphones" });

    expect(response.statusCode).toBe(503);
    expect(response.json()).toEqual({
      error: "Service Unavailable",
      message: "Search backend is temporarily unavailable",
    });
    expect(response.body).not.toContain("ETIMEDOUT");
    expect(response.body).not.toContain("stack");
  });
});
