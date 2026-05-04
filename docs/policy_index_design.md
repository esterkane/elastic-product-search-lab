# Policy Index Design

## Purpose

The governance layer is optional. Baseline search remains a stable lexical + boosted query against `products-read`. Merchandiser and personalization rules are data/config that can be enabled when a demo needs them.

## Policy Storage

Local lab storage:

- JSON file: `config/sample_search_policies.json`
- API environment variable: `SEARCH_POLICY_PATH=config/sample_search_policies.json`

Optional Elasticsearch storage:

- index name: `search-policies`
- helper body: `search_policy_index_body()` in `src/search/index_management.py`

The API currently loads the JSON file directly for simplicity. A production-shaped worker can cache policies from the optional index and refresh them on a short interval.

## Policy Schema

Common fields:

| Field | Purpose |
| --- | --- |
| `id` | Stable policy id for audit/debug |
| `enabled` | Allows merchandisers to turn policies on/off without deletion |
| `type` | `pin_boost`, `category_constraint`, `exclusion_filter`, or `seasonal_rewrite` |
| `priority` | Higher number wins when policies conflict |
| `queryMatch` | Case-insensitive substring matched against the user query |
| `reason` | Human explanation shown in debug output |

Initial policy types:

- `pin_boost`: adds a function-score weight for listed `productIds`.
- `category_constraint`: applies the highest-priority matching category filter.
- `exclusion_filter`: adds `must_not` product or brand filters.
- `seasonal_rewrite`: rewrites query text and/or emits a routing hint for debug/analytics.

## Conflict Ordering

Policy evaluation is deterministic:

1. Disabled policies are ignored.
2. Matching policies are sorted by descending `priority`, then ascending `id`.
3. Only the highest-priority matching category constraint applies.
4. Exclusions and boosts can stack.
5. Debug output lists every fired policy and its actions.

## Cohort Tags

Product design:

- `cohort_tags` is a small keyword array in the product mapping.
- Canonical products can derive `cohort_tags` from catalog `attributes.cohort_tags`.

Query-time design:

- `/search?cohorts=student,new_customer`
- each cohort adds a modest `function_score` term boost on `cohort_tags`
- default weight is `0.35`, intentionally below primary text relevance

## Debug Output

When `debug=true`, `/search` includes:

- fired policies with ids, types, priorities, reasons, and actions
- routing hints from seasonal policies
- requested cohort tags
- applied cohort boost weights
- the final Elasticsearch query DSL

## Operational Cautions

Keep policy counts small in the API path. Large policy sets should be precompiled or cached from the optional policy index. Merchandiser rules should be reviewed like data changes: policy ids and reasons matter because debug output is the operator-facing audit trail.
