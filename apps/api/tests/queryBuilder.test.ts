import { describe, expect, it } from "vitest";
import {
  buildBaselineBm25Query,
  buildBoostedRelevanceQuery,
  buildRankingExtensionFunctions,
  buildSearchDsl,
  buildSearchDslDebug,
  buildSuggestDsl,
} from "../src/search/queryBuilder.js";
import { evaluateSearchPolicies, type SearchPolicy } from "../src/search/policies.js";

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

  it("adds modest cohort boosts through the ranking extension hook", () => {
    expect(buildRankingExtensionFunctions({
      cohortTags: ["new_customer", "student"],
      merchandiserPolicies: ["pin-sponsored"],
    })).toEqual([
      { filter: { term: { cohort_tags: "new_customer" } }, weight: 0.35 },
      { filter: { term: { cohort_tags: "student" } }, weight: 0.35 },
    ]);
    expect(buildSearchDslDebug({ cohortTags: ["Student"] })).toEqual({
      cohortBoosts: [{ tag: "student", weight: 0.35 }],
    });
  });

  it("builds a separate bool-prefix suggest query", () => {
    expect(buildSuggestDsl({ q: "wire", size: 5 })).toEqual({
      size: 5,
      query: {
        multi_match: {
          query: "wire",
          type: "bool_prefix",
          fields: ["suggest_text", "suggest_text._2gram", "suggest_text._3gram", "title^2", "brand", "category"],
        },
      },
      _source: ["product_id", "title", "brand", "category", "suggest_text"],
    });
  });
});

describe("search policy evaluation", () => {
  const policies: SearchPolicy[] = [
    {
      id: "category-low",
      enabled: true,
      type: "category_constraint",
      priority: 10,
      queryMatch: "bag",
      category: "Accessories > Travel",
    },
    {
      id: "category-high",
      enabled: true,
      type: "category_constraint",
      priority: 30,
      queryMatch: "bag",
      category: "Accessories > Laptop Bags",
      reason: "Prefer laptop bag category",
    },
    {
      id: "disabled-pin",
      enabled: false,
      type: "pin_boost",
      priority: 100,
      queryMatch: "bag",
      productIds: ["P-disabled"],
    },
    {
      id: "pin-active",
      enabled: true,
      type: "pin_boost",
      priority: 20,
      queryMatch: "bag",
      productIds: ["P-active"],
      boost: 3,
    },
    {
      id: "exclude-active",
      enabled: true,
      type: "exclusion_filter",
      priority: 15,
      queryMatch: "bag",
      excludeBrands: ["BlockedBrand"],
    },
  ];

  it("orders policy conflicts by priority and ignores disabled policies", () => {
    const evaluation = evaluateSearchPolicies(policies, "laptop bag");

    expect(evaluation.filters).toEqual([{ term: { category: "accessories > laptop bags" } }]);
    expect(evaluation.boostFunctions).toEqual([{ filter: { ids: { values: ["P-active"] } }, weight: 3 }]);
    expect(evaluation.mustNot).toEqual([{ terms: { brand: ["blockedbrand"] } }]);
    expect(evaluation.firedPolicies.map((policy) => policy.id)).toEqual(["category-high", "pin-active", "exclude-active"]);
    expect(evaluation.firedPolicies).not.toContainEqual(expect.objectContaining({ id: "disabled-pin" }));
  });

  it("records seasonal rewrites and routing hints", () => {
    const evaluation = evaluateSearchPolicies([
      {
        id: "holiday",
        enabled: true,
        type: "seasonal_rewrite",
        priority: 50,
        queryMatch: "holiday gifts",
        rewriteQuery: "holiday gifts popular",
        routingHint: "holiday-guide",
      },
    ], "holiday gifts");

    expect(evaluation.queryText).toBe("holiday gifts popular");
    expect(evaluation.routingHints).toEqual(["holiday-guide"]);
    expect(evaluation.firedPolicies[0]).toMatchObject({ id: "holiday", actions: ["rewrite_query"] });
  });
});
