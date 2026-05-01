import { describe, expect, it } from "vitest";
import { buildBaselineBm25Query, buildBoostedRelevanceQuery, buildSearchDsl } from "../src/search/queryBuilder.js";

const baseParams = { size: 10, debug: false };

describe("product search query builder", () => {
  it("builds the baseline BM25 query with weighted fields and filters", () => {
    const query = buildBaselineBm25Query({
      ...baseParams,
      q: "wireless headphones",
      category: "Electronics > Headphones",
      brand: "Sony",
      availability: "in_stock",
      minPrice: 50,
      maxPrice: 200,
    });

    expect(query).toEqual({
      bool: {
        must: [
          {
            multi_match: {
              query: "wireless headphones",
              fields: ["title^4", "brand^2", "category^1.5", "description^0.8", "catalog_text^0.5"],
              type: "best_fields",
              operator: "and",
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
    });
  });

  it("wraps baseline relevance in mild popularity and recency boosts", () => {
    const query = buildBoostedRelevanceQuery({ ...baseParams, q: "usb c charger" });

    expect(query).toMatchObject({
      function_score: {
        query: {
          bool: {
            must: [
              {
                multi_match: {
                  query: "usb c charger",
                },
              },
            ],
          },
        },
        score_mode: "sum",
        boost_mode: "sum",
        functions: [
          {
            field_value_factor: {
              field: "popularity_score",
              factor: 0.02,
              modifier: "sqrt",
              missing: 0,
            },
          },
          {
            gauss: {
              updated_at: {
                origin: "now",
                scale: "30d",
                offset: "7d",
                decay: 0.5,
              },
            },
            weight: 0.2,
          },
        ],
      },
    });
  });

  it("uses match_all when q is absent", () => {
    const query = buildBaselineBm25Query(baseParams);

    expect(query).toMatchObject({
      bool: {
        must: [{ match_all: {} }],
      },
    });
  });

  it("adds explain and profile only in debug mode", () => {
    expect(buildSearchDsl({ ...baseParams, q: "mouse" })).not.toHaveProperty("explain");
    expect(buildSearchDsl({ ...baseParams, q: "mouse" })).not.toHaveProperty("profile");

    expect(buildSearchDsl({ ...baseParams, q: "mouse", debug: true })).toMatchObject({
      explain: true,
      profile: true,
    });
  });

  it("can disable function_score boosts for a pure baseline query", () => {
    const dsl = buildSearchDsl({ ...baseParams, q: "mouse", boost: false });

    expect(dsl).toMatchObject({
      query: {
        bool: {
          must: [
            {
              multi_match: {
                query: "mouse",
              },
            },
          ],
        },
      },
      sort: ["_score"],
    });
  });
});