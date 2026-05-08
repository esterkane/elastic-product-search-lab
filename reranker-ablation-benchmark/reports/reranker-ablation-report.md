# Reranker Ablation Benchmark

Generated: `2026-05-08T09:16:58.356098+00:00`
Top-k reranked: `5`

## ROI Summary

| Baseline | Candidate | nDCG@5 delta | MRR@5 delta | Precision@3 delta | Recall@5 delta | p95 latency delta |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| baseline | reranked | +0.244 | +0.000 | +0.000 | +0.000 | +39.5 ms |

## When Reranking Helps

Use reranking conditionally for ambiguous, high-value, or answer-generating searches; keep first-stage retrieval for low-latency browsing.

## baseline

First-stage retrieval order, no reranker.

| Metric | Value |
| --- | ---: |
| nDCG@5 | 0.756 |
| MRR@5 | 1.000 |
| Precision@3 | 1.000 |
| Recall@5 | 1.000 |
| p50 latency | 44.0 ms |
| p95 latency | 56.9 ms |

| Query | Top result | nDCG@5 | MRR@5 | Ranked ids |
| --- | --- | ---: | ---: | --- |
| q-hybrid | p-keyword-only | 0.753 | 1.000 | p-keyword-only, p-hybrid-guide, p-rerank-model, p-returns-policy, p-filtering |
| q-latency | p-bulk-ingest | 0.755 | 1.000 | p-bulk-ingest, p-latency-tuning, p-vector-filter, p-size-chart, p-cache-policy |
| q-zero | p-empty-state | 0.758 | 1.000 | p-empty-state, p-no-match-help, p-autocorrect, p-fuzzy-fallback, p-homepage |

## reranked

Same top-5 candidate set reranked by deterministic cross-encoder score.

| Metric | Value |
| --- | ---: |
| nDCG@5 | 1.000 |
| MRR@5 | 1.000 |
| Precision@3 | 1.000 |
| Recall@5 | 1.000 |
| p50 latency | 71.0 ms |
| p95 latency | 96.4 ms |

| Query | Top result | nDCG@5 | MRR@5 | Ranked ids |
| --- | --- | ---: | ---: | --- |
| q-hybrid | p-hybrid-guide | 1.000 | 1.000 | p-hybrid-guide, p-rerank-model, p-filtering, p-keyword-only, p-returns-policy |
| q-latency | p-latency-tuning | 1.000 | 1.000 | p-latency-tuning, p-vector-filter, p-cache-policy, p-bulk-ingest, p-size-chart |
| q-zero | p-no-match-help | 1.000 | 1.000 | p-no-match-help, p-autocorrect, p-fuzzy-fallback, p-empty-state, p-homepage |
