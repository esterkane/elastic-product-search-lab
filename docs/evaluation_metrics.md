# Evaluation Metrics

Offline relevance evaluation turns search tuning into a measurable workflow. Instead of judging a few result pages by eye, the lab runs known queries against graded query-product judgments and reports metrics that capture different ranking behaviors.

## Judgment Scale

The sample judgments use four grades:

- `exact = 3`: the product directly satisfies the query.
- `substitute = 2`: the product is a reasonable alternative.
- `complement = 1`: the product is related but not the main intent.
- `irrelevant = 0`: the product should not satisfy the query.

This mirrors the idea behind ESCI-style product search evaluation, where not all relevant-looking products are equally useful.

## Precision@k

Precision@k measures the share of the top `k` results that are relevant. In this lab, any judgment above `0` counts as relevant.

Precision@10 is easy to explain because it answers: how many of the first ten results are at least somewhat useful? The downside is that it can hide ranking quality issues. A result set with the exact match at rank 10 can have the same Precision@10 as one with the exact match at rank 1.

## MRR

Mean Reciprocal Rank measures how early the first relevant result appears. A query with a relevant result at rank 1 gets `1.0`; rank 2 gets `0.5`; rank 10 gets `0.1`.

MRR is useful for product search because users often scan from the top and expect the first good result quickly. It is especially helpful for navigational or highly specific queries such as a known brand or product type.

## DCG@k

Discounted Cumulative Gain rewards relevant documents near the top of the ranking. It uses graded relevance, so an exact match contributes more than a substitute or complement. The discount lowers the value of results as their rank gets deeper.

## nDCG@k

Normalized DCG compares the actual ranking against the best possible ranking for the available judgments. The result is usually between `0` and `1`, where `1` means the ranked list is ideal for the judged documents.

nDCG is a good fit for graded relevance because product search often has shades of usefulness. A substitute is better than an irrelevant product, but worse than the exact item the shopper intended. nDCG captures that nuance better than binary precision.

## Product Search Mapping

These metrics map naturally to marketplace search:

- Precision@10 checks whether the first page is broadly useful.
- MRR checks whether shoppers see a good result immediately.
- nDCG@10 checks whether exact matches, substitutes, and complements are ordered sensibly.
- Query-level rows expose regressions that aggregate averages can hide.

## Before A/B Testing

Offline evaluation should run before A/B testing. It provides a fast safety check for mapping changes, boosts, analyzers, filters, and hybrid retrieval experiments. If a change damages offline metrics or important query-level examples, it should usually be fixed before real users see it.

A/B tests still matter because offline judgments cannot capture every user behavior. After offline metrics look healthy, online experiments can validate click-through, conversion, zero-result recovery, latency, and long-term marketplace outcomes.