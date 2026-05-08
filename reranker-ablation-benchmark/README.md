# Reranker Ablation Benchmark

This benchmark compares first-stage retrieval against reranked retrieval on the exact same judged top-k candidate set. It is intentionally small and deterministic so the quality/latency trade-off is easy to inspect.

## What It Tests

- `baseline`: keep first-stage retrieval order.
- `reranked`: take the same top-5 candidates and reorder them by deterministic reranker score.

The benchmark reports:

- nDCG@5
- MRR@5
- Precision@3
- Recall@5
- p50 and p95 latency
- deltas versus baseline

## Run

From this directory:

```powershell
python scripts/reranker_ablation.py
python -m pytest tests -p no:cacheprovider
```

If `python` is not on PATH, use an explicit Python executable.

Outputs:

- `reports/reranker-ablation-report.json`
- `reports/reranker-ablation-report.md`

## When Reranking Helps

Reranking is most useful when the first-stage retriever has high recall but imperfect ordering: the right documents are already in the top-k candidate set, but exact keyword, dense, or hybrid scores place weaker candidates ahead of the best answer evidence.

It should usually be conditional rather than universal:

- Enable for answer generation, ambiguous queries, support workflows, and high-value searches where better ordering matters.
- Skip for low-latency browse flows, obvious navigational queries, or candidate sets where first-stage retrieval is already confident.
- Keep top-k explicit. This benchmark uses top-5 to make the extra compute budget visible.

## Assumptions

The reranker scores are deterministic fixture scores, not a model integration. That keeps the artifact reproducible while still demonstrating the evaluation shape a real cross-encoder or hosted reranker would use.
