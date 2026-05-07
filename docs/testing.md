# Testing And Quality Gates

This project uses a local quality program for search changes, not just endpoint smoke tests. The goal is to make relevance, performance, and resilience regressions visible before a change ships.

## Offline ESCI Evaluation

Run the default fixture-backed evaluation:

```powershell
python scripts/search_quality_program.py
```

Outputs:

- `reports/search-quality-report.json`: machine-readable metrics, gates, query rows, shard scenarios, and resilience matrix.
- `reports/search-quality-decision.md`: human-readable decision summary that names shippable and blocked changes.

The default loop now includes a measurable before/after comparison:

- `baseline-bm25`: lexical/BM25 candidate order.
- `hybrid-rrf`: lexical and dense candidate sets fused with reciprocal rank fusion using `rrf_rank_constant=60`.

The gate thresholds and baseline-vs-candidate comparison are configured in `config/search-quality-gate.json`. RRF adds latency because it executes two retrieval channels before fusion, so the report records both relevance deltas and p95 latency delta.

The relevance evaluator accepts ESCI labels as `E`, `S`, `C`, and `I`, mapped to Exact `3`, Substitute `2`, Complement `1`, and Irrelevant `0`. It reports:

- `nDCG@10`
- `Precision@5`
- `MRR@10`
- `Recall@5` and `Recall@10`
- zero-result rate

To evaluate external judgments and search runs:

```powershell
python scripts/search_quality_program.py --judgments path\to\judgments.jsonl --runs path\to\runs.json
```

Judgment rows should include `query_id`, `query`, `doc_id`, and either `esci_label`, `grade`, or `judgment`. Run JSON should include `name`, `strategy`, `latency_ms`, `request_count`, and `duration_seconds`. Use `ranked_results` for pre-ranked BM25 or reranked runs. Use `channel_results` for `hybrid-rrf` runs:

```json
{
  "name": "hybrid-rrf",
  "strategy": "hybrid-rrf",
  "channel_results": {
    "q1": {
      "lexical": ["doc-a", "doc-b"],
      "dense": ["doc-b", "doc-c"]
    }
  },
  "latency_ms": [42, 55, 71],
  "request_count": 100,
  "duration_seconds": 4
}
```

## Performance Benchmarks

The harness records:

- p50, p95, and p99 latency
- throughput in queries per second
- shard-size scenarios such as `1_shard_50k_docs`, `3_shards_250k_docs`, and `6_shards_1m_docs`

Default pass/fail gates are intentionally explicit: p95 latency must be at or below `180 ms`, p99 at or below `260 ms`, and throughput at or above `25 qps`.

## Resilience Matrix

Every release candidate should cover:

| Scenario | Required recovery behavior |
| --- | --- |
| replay | Reprocess failed events without creating duplicate products or chunks. |
| idempotency | Repeated writes keep the same final state. |
| 429/backoff | Retry with bounded jittered backoff and preserve the request budget. |
| partial-cluster degradation | Serve degraded lexical or semantic results with a warning instead of hard failing. |
| alias rollback | Restore the read alias to the last healthy index. |
| soft-delete merge | Prevent stale update events from resurrecting soft-deleted records. |

## Ship Gates

A search change should ship only when all gates pass:

- nDCG@10 >= `0.72`
- Precision@5 >= `0.60`
- MRR@10 >= `0.68`
- Recall@10 >= `0.72`
- zero-result rate <= `0.05`
- p95 latency <= `180 ms`
- p99 latency <= `260 ms`
- throughput >= `25 qps`
- every resilience scenario is `pass`

Use `--fail-on-gate` in CI when any blocked candidate should fail the job:

```powershell
python scripts/search_quality_program.py --fail-on-gate
```
