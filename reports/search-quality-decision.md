# Search Quality Decision Summary

Generated: `2026-05-07T11:03:57.850202+00:00`

## Decision

- Recommendation: **review_required**
- Shippable changes: baseline-bm25, hybrid-rrf, candidate-good
- Blocked changes: candidate-bad

## Before/After

| Baseline | Candidate | nDCG@10 delta | Recall@10 delta | p95 latency delta | Result |
| --- | --- | ---: | ---: | ---: | --- |
| baseline-bm25 | hybrid-rrf | +0.111 | +0.000 | +12.5 ms | pass |

## baseline-bm25 (bm25): SHIPS

Keyword/BM25 baseline using the lexical candidate set only.

| Gate | Value | Threshold | Result |
| --- | ---: | ---: | --- |
| nDCG@10 | 0.855 | 0.720 | pass |
| Precision@5 | 0.650 | 0.600 | pass |
| MRR@10 | 1.000 | 0.680 | pass |
| Recall@10 | 1.000 | 0.720 | pass |
| Zero-result rate | 0.000 | 0.050 | pass |
| p95 latency | 120.500 | 180.000 | pass |
| p99 latency | 128.100 | 260.000 | pass |
| Throughput | 31.000 | 25.000 | pass |
| Resilience: replay | pass | pass | pass |
| Resilience: idempotency | pass | pass | pass |
| Resilience: 429/backoff | pass | pass | pass |
| Resilience: partial-cluster degradation | pass | pass | pass |
| Resilience: alias rollback | pass | pass | pass |
| Resilience: soft-delete merge | pass | pass | pass |

### Why

- Relevance: nDCG@10 `0.855`, Precision@5 `0.650`, MRR@10 `1.000`, Recall@10 `1.000`, zero-result rate `0.000`.
- Performance: p50 `52.0 ms`, p95 `120.5 ms`, p99 `128.1 ms`, throughput `31.0 qps`.
- Resilience: pass rate `1.000` across replay, idempotency, 429/backoff, partial-cluster degradation, alias rollback, and soft-delete merge scenarios.

### Recovery Matrix

| Scenario | Status | Expected recovery | Observed |
| --- | --- | --- | --- |
| replay | pass | Reprocess failed events without duplicates. | Replay preserves event ids. |
| idempotency | pass | Repeated upsert has the same final state. | Second write is a no-op. |
| 429/backoff | pass | Retry with jittered exponential backoff and preserve request budget. | Third attempt succeeds. |
| partial-cluster degradation | pass | Serve degraded lexical or semantic results with warning. | Semantic failure returns lexical results. |
| alias rollback | pass | Rollback read alias to previous healthy index. | Alias returns to products_v41. |
| soft-delete merge | pass | Merged updates must not resurrect soft-deleted products. | Deleted sku remains hidden. |

## hybrid-rrf (hybrid-rrf): SHIPS

Lexical and dense candidate sets fused with reciprocal rank fusion before optional reranking.

| Gate | Value | Threshold | Result |
| --- | ---: | ---: | --- |
| nDCG@10 | 0.966 | 0.720 | pass |
| Precision@5 | 0.650 | 0.600 | pass |
| MRR@10 | 1.000 | 0.680 | pass |
| Recall@10 | 1.000 | 0.720 | pass |
| Zero-result rate | 0.000 | 0.050 | pass |
| p95 latency | 133.000 | 180.000 | pass |
| p99 latency | 142.600 | 260.000 | pass |
| Throughput | 27.500 | 25.000 | pass |
| Resilience: replay | pass | pass | pass |
| Resilience: idempotency | pass | pass | pass |
| Resilience: 429/backoff | pass | pass | pass |
| Resilience: partial-cluster degradation | pass | pass | pass |
| Resilience: alias rollback | pass | pass | pass |
| Resilience: soft-delete merge | pass | pass | pass |

### Why

- Relevance: nDCG@10 `0.966`, Precision@5 `0.650`, MRR@10 `1.000`, Recall@10 `1.000`, zero-result rate `0.000`.
- Performance: p50 `64.0 ms`, p95 `133.0 ms`, p99 `142.6 ms`, throughput `27.5 qps`.
- Resilience: pass rate `1.000` across replay, idempotency, 429/backoff, partial-cluster degradation, alias rollback, and soft-delete merge scenarios.

### Recovery Matrix

| Scenario | Status | Expected recovery | Observed |
| --- | --- | --- | --- |
| replay | pass | Reprocess failed events without duplicates. | Replay preserves event ids. |
| idempotency | pass | Repeated upsert has the same final state. | Second write is a no-op. |
| 429/backoff | pass | Retry with jittered exponential backoff and preserve request budget. | Third attempt succeeds. |
| partial-cluster degradation | pass | Serve degraded lexical or semantic results with warning. | Semantic failure returns lexical results. |
| alias rollback | pass | Rollback read alias to previous healthy index. | Alias returns to products_v41. |
| soft-delete merge | pass | Merged updates must not resurrect soft-deleted products. | Deleted sku remains hidden. |

## candidate-good (hybrid-rerank): SHIPS

Hybrid retrieval with reranker scores applied after fusion.

| Gate | Value | Threshold | Result |
| --- | ---: | ---: | --- |
| nDCG@10 | 1.000 | 0.720 | pass |
| Precision@5 | 0.650 | 0.600 | pass |
| MRR@10 | 1.000 | 0.680 | pass |
| Recall@10 | 1.000 | 0.720 | pass |
| Zero-result rate | 0.000 | 0.050 | pass |
| p95 latency | 133.000 | 180.000 | pass |
| p99 latency | 142.600 | 260.000 | pass |
| Throughput | 27.500 | 25.000 | pass |
| Resilience: replay | pass | pass | pass |
| Resilience: idempotency | pass | pass | pass |
| Resilience: 429/backoff | pass | pass | pass |
| Resilience: partial-cluster degradation | pass | pass | pass |
| Resilience: alias rollback | pass | pass | pass |
| Resilience: soft-delete merge | pass | pass | pass |

### Why

- Relevance: nDCG@10 `1.000`, Precision@5 `0.650`, MRR@10 `1.000`, Recall@10 `1.000`, zero-result rate `0.000`.
- Performance: p50 `64.0 ms`, p95 `133.0 ms`, p99 `142.6 ms`, throughput `27.5 qps`.
- Resilience: pass rate `1.000` across replay, idempotency, 429/backoff, partial-cluster degradation, alias rollback, and soft-delete merge scenarios.

### Recovery Matrix

| Scenario | Status | Expected recovery | Observed |
| --- | --- | --- | --- |
| replay | pass | Reprocess failed events without duplicates. | Replay preserves event ids. |
| idempotency | pass | Repeated upsert has the same final state. | Second write is a no-op. |
| 429/backoff | pass | Retry with jittered exponential backoff and preserve request budget. | Third attempt succeeds. |
| partial-cluster degradation | pass | Serve degraded lexical or semantic results with warning. | Semantic failure returns lexical results. |
| alias rollback | pass | Rollback read alias to previous healthy index. | Alias returns to products_v41. |
| soft-delete merge | pass | Merged updates must not resurrect soft-deleted products. | Deleted sku remains hidden. |

## candidate-bad (regression): DO NOT SHIP

Known-bad run that demonstrates gate failure behavior.

| Gate | Value | Threshold | Result |
| --- | ---: | ---: | --- |
| nDCG@10 | 0.197 | 0.720 | fail |
| Precision@5 | 0.200 | 0.600 | fail |
| MRR@10 | 0.250 | 0.680 | fail |
| Recall@10 | 0.333 | 0.720 | fail |
| Zero-result rate | 0.500 | 0.050 | fail |
| p95 latency | 642.500 | 180.000 | fail |
| p99 latency | 696.500 | 260.000 | fail |
| Throughput | 12.000 | 25.000 | fail |
| Resilience: replay | pass | pass | pass |
| Resilience: idempotency | pass | pass | pass |
| Resilience: 429/backoff | fail | pass | fail |
| Resilience: partial-cluster degradation | pass | pass | pass |
| Resilience: alias rollback | pass | pass | pass |
| Resilience: soft-delete merge | pass | pass | pass |

### Why

- Relevance: nDCG@10 `0.197`, Precision@5 `0.200`, MRR@10 `0.250`, Recall@10 `0.333`, zero-result rate `0.500`.
- Performance: p50 `305.0 ms`, p95 `642.5 ms`, p99 `696.5 ms`, throughput `12.0 qps`.
- Resilience: pass rate `0.833` across replay, idempotency, 429/backoff, partial-cluster degradation, alias rollback, and soft-delete merge scenarios.

### Recovery Matrix

| Scenario | Status | Expected recovery | Observed |
| --- | --- | --- | --- |
| replay | pass | Reprocess failed events without duplicates. | Replay preserves event ids. |
| idempotency | pass | Repeated upsert has the same final state. | Second write is a no-op. |
| 429/backoff | fail | Retry with jittered exponential backoff and preserve request budget. | Retries stampede immediately and exhaust the budget. |
| partial-cluster degradation | pass | Serve degraded lexical or semantic results with warning. | Semantic failure returns lexical results. |
| alias rollback | pass | Rollback read alias to previous healthy index. | Alias returns to products_v41. |
| soft-delete merge | pass | Merged updates must not resurrect soft-deleted products. | Deleted sku remains hidden. |

