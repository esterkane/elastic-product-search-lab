import { readFileSync } from "node:fs";

export type SearchPolicyType = "pin_boost" | "category_constraint" | "exclusion_filter" | "seasonal_rewrite";

export type SearchPolicy = {
  id: string;
  enabled: boolean;
  type: SearchPolicyType;
  priority: number;
  queryMatch: string;
  productIds?: string[];
  category?: string;
  excludeProductIds?: string[];
  excludeBrands?: string[];
  boost?: number;
  rewriteQuery?: string;
  routingHint?: string;
  reason?: string;
};

export type FiredPolicy = {
  id: string;
  type: SearchPolicyType;
  priority: number;
  reason?: string;
  actions: string[];
};

export type PolicyEvaluation = {
  queryText?: string;
  filters: Record<string, unknown>[];
  mustNot: Record<string, unknown>[];
  boostFunctions: Record<string, unknown>[];
  firedPolicies: FiredPolicy[];
  routingHints: string[];
};

export function loadPoliciesFromFile(path?: string): SearchPolicy[] {
  if (!path) return [];
  const raw = JSON.parse(readFileSync(path, "utf-8")) as unknown;
  if (Array.isArray(raw)) return raw.map(validatePolicy);
  if (raw && typeof raw === "object" && "policies" in raw && Array.isArray((raw as { policies: unknown }).policies)) {
    return (raw as { policies: unknown[] }).policies.map(validatePolicy);
  }
  throw new Error("Policy file must contain an array or an object with a policies array");
}

function validatePolicy(raw: unknown): SearchPolicy {
  if (!raw || typeof raw !== "object") throw new Error("Policy must be an object");
  const policy = raw as Partial<SearchPolicy>;
  if (!policy.id || !policy.type || !policy.queryMatch) throw new Error("Policy requires id, type, and queryMatch");
  return {
    id: String(policy.id),
    enabled: policy.enabled ?? true,
    type: policy.type,
    priority: Number(policy.priority ?? 0),
    queryMatch: String(policy.queryMatch),
    productIds: policy.productIds?.map(String),
    category: policy.category,
    excludeProductIds: policy.excludeProductIds?.map(String),
    excludeBrands: policy.excludeBrands?.map(String),
    boost: policy.boost === undefined ? undefined : Number(policy.boost),
    rewriteQuery: policy.rewriteQuery,
    routingHint: policy.routingHint,
    reason: policy.reason,
  };
}

function matchesQuery(policy: SearchPolicy, queryText?: string): boolean {
  const query = queryText?.trim().toLowerCase();
  if (!query) return false;
  return query.includes(policy.queryMatch.trim().toLowerCase());
}

function fired(policy: SearchPolicy, actions: string[]): FiredPolicy {
  return { id: policy.id, type: policy.type, priority: policy.priority, reason: policy.reason, actions };
}

export function evaluateSearchPolicies(policies: SearchPolicy[], queryText?: string): PolicyEvaluation {
  const matched = policies
    .filter((policy) => policy.enabled && matchesQuery(policy, queryText))
    .sort((left, right) => right.priority - left.priority || left.id.localeCompare(right.id));

  const evaluation: PolicyEvaluation = {
    queryText,
    filters: [],
    mustNot: [],
    boostFunctions: [],
    firedPolicies: [],
    routingHints: [],
  };

  const rewrite = matched.find((policy) => policy.type === "seasonal_rewrite" && policy.rewriteQuery);
  if (rewrite?.rewriteQuery) {
    evaluation.queryText = rewrite.rewriteQuery;
    evaluation.firedPolicies.push(fired(rewrite, ["rewrite_query"]));
  }

  const categoryConstraint = matched.find((policy) => policy.type === "category_constraint" && policy.category);
  if (categoryConstraint?.category) {
    evaluation.filters.push({ term: { category: categoryConstraint.category.toLowerCase() } });
    evaluation.firedPolicies.push(fired(categoryConstraint, ["filter_category"]));
  }

  for (const policy of matched) {
    if (policy.type === "pin_boost" && policy.productIds?.length) {
      evaluation.boostFunctions.push({
        filter: { ids: { values: policy.productIds } },
        weight: policy.boost ?? 5,
      });
      evaluation.firedPolicies.push(fired(policy, ["boost_products"]));
    }
    if (policy.type === "exclusion_filter") {
      const actions: string[] = [];
      if (policy.excludeProductIds?.length) {
        evaluation.mustNot.push({ ids: { values: policy.excludeProductIds } });
        actions.push("exclude_products");
      }
      if (policy.excludeBrands?.length) {
        evaluation.mustNot.push({ terms: { brand: policy.excludeBrands.map((brand) => brand.toLowerCase()) } });
        actions.push("exclude_brands");
      }
      if (actions.length) evaluation.firedPolicies.push(fired(policy, actions));
    }
    if (policy.type === "seasonal_rewrite" && policy.routingHint) {
      evaluation.routingHints.push(policy.routingHint);
      if (!evaluation.firedPolicies.some((firedPolicy) => firedPolicy.id === policy.id)) {
        evaluation.firedPolicies.push(fired(policy, ["routing_hint"]));
      }
    }
  }

  return evaluation;
}
