import { describe, expect, it } from "vitest";
import { buildSearchDsl } from "../src/search/queryBuilder.js";

const baseParams = { size: 10, debug: false };

describe("buildSearchDsl", () => {
  it("builds a weighted multi_match query with filters", () => {
    const dsl = buildSearchDsl({
      ...baseParams,
      q: "wireless headphones",
      category: "Electronics > Headphones",
      brand: "Sony",
      availability: "in_stock",
      minPrice: 50,
      maxPrice: 200,
    });

    expect(dsl).toMatchObject({
      size: 10,
      query: {
        bool: {
          must: [
            {
              multi_match: {
                query: "wireless headphones",
                fields: ["title^3", "brand^2", "category^1.5", "description", "catalog_text"],
              },
            },
          ],
          filter: [
            { term: { category: "electronics > headphones" } },
            { term: { brand: "sony" } },
            { term: { availability: "in_stock" } },
            { range: { price: { gte: 50, lte: 200 } } },
          ],
        },
      },
      sort: ["_score"],
    });
  });

  it("uses match_all when q is absent", () => {
    const dsl = buildSearchDsl(baseParams);

    expect(dsl).toMatchObject({
      query: {
        bool: {
          must: [{ match_all: {} }],
        },
      },
    });
  });
});