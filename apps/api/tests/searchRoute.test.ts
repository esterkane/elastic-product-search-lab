import { afterEach, describe, expect, it } from "vitest";
import { buildTestApp } from "./helpers.js";

let app: ReturnType<typeof buildTestApp> | undefined;

afterEach(async () => {
  await app?.close();
  app = undefined;
});

describe("GET /search", () => {
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
