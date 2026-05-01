# Search Performance Report

Local benchmark results for product-search strategies. Latency values are milliseconds.

| Strategy | Count | Success | Error Rate | Timeout Rate | p50 | p95 | p99 | Min | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_lexical | 16 | 16 | 0.000 | 0.000 | 46.61 | 47.58 | 47.68 | 44.43 | 47.70 |
| boosted_lexical | 16 | 16 | 0.000 | 0.000 | 47.59 | 48.99 | 49.41 | 44.00 | 49.51 |
| hybrid_rrf | 16 | 16 | 0.000 | 0.000 | 99.19 | 102.59 | 102.76 | 93.36 | 102.80 |

Tail latency should be reviewed alongside relevance metrics. A relevance gain that doubles p99 latency may be a regression for real users.
