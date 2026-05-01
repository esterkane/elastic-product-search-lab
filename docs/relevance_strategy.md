# Relevance Strategy

Product search relevance starts with a simple question: did the product match the shopper's intent in the fields where intent is most likely to appear? This lab keeps ranking decisions explicit and testable so experiments can be compared instead of guessed.

## Baseline Query

The baseline query is a BM25 `multi_match` over product text fields:

- `title^4`
- `brand^2`
- `category^1.5`
- `description^0.8`
- `catalog_text^0.5`

Filters for `category`, `brand`, `availability`, and price ranges are applied in filter context. They narrow the candidate set without adding score noise.

## Tuned Boosted Query

The tuned query wraps the baseline BM25 query in a mild `function_score`:

- `popularity_score` uses a small square-root field-value factor.
- `updated_at` uses a gentle recency decay.

These boosts are intentionally small. Their job is to break ties and prefer healthy, fresh catalog records, not to overpower textual relevance.

## Filters Versus Scoring

Availability should usually be a filter, not a scoring field. If a shopper asks for in-stock items, unavailable products should be excluded rather than merely ranked lower. Treating availability as a score can leak out-of-stock products into top results.

Price range, brand, and category behave similarly when the user chooses them as facets. Once the user asks for a constraint, respecting the constraint is more important than treating it as soft relevance evidence.

## Why Title Matches Matter

Product titles usually contain the highest-density description of what the item is: `wireless mouse`, `usb c charger`, `running shoes`, or `noise cancelling headphones`. A title match should usually beat the same term appearing only in a long description because the title is closer to explicit shopping intent.

Brand and category matches also matter, but they are less specific. Description and combined catalog text are useful recall fields, but they can contain broad language that should not dominate ranking.

## Popularity Risk

Popularity is useful but dangerous. If it is overweighted, popular generic products can hide exact niche matches. Popularity should be capped, transformed, or used gently until offline and online evidence proves it helps.

## Hybrid and Reranking Experiments

Hybrid retrieval adds dense-vector recall to the lexical baseline. Reranking optionally reorders a smaller candidate window after broad retrieval. Both features can improve semantic relevance for some queries and regress exact-match behavior for others, so they remain optional experiments in this lab.

## Offline Metrics

Offline metrics reduce guesswork by comparing query changes against a stable judgment set. This lab uses nDCG@k, MRR, and Precision@k to identify whether a ranking change improves relevant top results or only looks better in a few hand-picked examples.

Reports should include aggregate metrics and per-query rows. A change can improve average nDCG while damaging important head or long-tail queries.

## A/B Tests

A/B tests complement offline evaluation. Offline metrics tell us whether a change aligns with known judgments; online experiments show whether real users search, click, add to cart, and recover from bad results differently. This lab does not implement A/B testing, but it prepares the offline evidence that should come before an online experiment.
