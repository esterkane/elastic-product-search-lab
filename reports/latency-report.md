# Search Performance Report

Local benchmark results for product-search strategies. Latency values are milliseconds.

| Strategy | Count | Success | Error Rate | Timeout Rate | p50 | p95 | p99 | Min | Max | Avg |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_bm25 | 200 | 200 | 0.000 | 0.000 | 6.87 | 8.85 | 10.59 | 4.86 | 49.98 | 7.22 |
| boosted_bm25 | 200 | 200 | 0.000 | 0.000 | 182.46 | 248.24 | 262.83 | 104.05 | 286.66 | 181.38 |
| enriched_profile | 200 | 200 | 0.000 | 0.000 | 130.13 | 204.27 | 228.79 | 50.21 | 321.37 | 137.89 |

Tail latency should be reviewed alongside relevance metrics. A relevance gain that doubles p99 latency may be a regression for real users.
