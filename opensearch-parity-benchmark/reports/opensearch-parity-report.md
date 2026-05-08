# OpenSearch Parity Benchmark Report

Generated: `2026-05-07T12:17:04.166856+00:00`
Engine: `OpenSearch 2.19.1`
Index: `product_support_docs`

## Before/After

| Baseline | Candidate | nDCG@10 delta | Recall@10 delta | p95 latency delta |
| --- | --- | ---: | ---: | ---: |
| bm25 | hybrid_rrf | +0.001 | +0.083 | +4.3 ms |

## bm25

| Metric | Value |
| --- | ---: |
| nDCG@10 | 0.987 |
| Precision@5 | 0.550 |
| MRR@10 | 1.000 |
| Recall@10 | 0.917 |
| p50 latency | 17.3 ms |
| p95 latency | 39.8 ms |

## hybrid_rrf

| Metric | Value |
| --- | ---: |
| nDCG@10 | 0.988 |
| Precision@5 | 0.550 |
| MRR@10 | 1.000 |
| Recall@10 | 1.000 |
| p50 latency | 20.7 ms |
| p95 latency | 44.2 ms |
