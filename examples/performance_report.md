# Search Performance Report

Local benchmark results for product-search strategies. Latency values are milliseconds.

## Why This Matters

Search relevance work is incomplete without latency measurement. A strategy can improve nDCG while making p95 or p99 worse, which may be unacceptable for a user-facing search API.

| Strategy | Count | Success | Error Rate | Timeout Rate | p50 | p95 | p99 | Min | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_lexical | 16 | 16 | 0.000 | 0.000 | 46.61 | 47.58 | 47.68 | 44.43 | 47.70 |
| boosted_lexical | 16 | 16 | 0.000 | 0.000 | 47.59 | 48.99 | 49.41 | 44.00 | 49.51 |
| hybrid_rrf | 16 | 16 | 0.000 | 0.000 | 99.19 | 102.59 | 102.76 | 93.36 | 102.80 |

## Interpretation

The local hybrid path is slower than lexical retrieval because it performs vector-related work and fusion. That is acceptable for a lab only if relevance improves enough to justify the cost. In a production setting, this table would be reviewed alongside nDCG@10, MRR, timeout rate, rejected requests, and cluster health.

Tail latency should be reviewed alongside relevance metrics. A relevance gain that doubles p99 latency may still be a regression for real users.
