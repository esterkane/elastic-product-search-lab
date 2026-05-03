# Search Performance Report

Local benchmark results for product-search strategies. Latency values are milliseconds.

| Strategy | Count | Success | Error Rate | Timeout Rate | p50 | p95 | p99 | Min | Max | Avg |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_bm25 | 500 | 500 | 0.000 | 0.000 | 6.66 | 45.52 | 49.69 | 3.90 | 230.04 | 9.29 |
| boosted_bm25 | 500 | 500 | 0.000 | 0.000 | 188.85 | 283.08 | 348.16 | 52.07 | 394.53 | 185.21 |
| enriched_profile | 500 | 500 | 0.000 | 0.000 | 146.71 | 249.96 | 283.52 | 40.12 | 377.26 | 147.88 |

Tail latency should be reviewed alongside relevance metrics. A relevance gain that doubles p99 latency may be a regression for real users.
