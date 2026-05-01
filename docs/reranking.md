# Optional Semantic Reranking

Reranking is an advanced retrieval pattern, not an MVP requirement for this lab. The core product-search flow should work well with explicit mappings, BM25, filters, boosts, offline judgments, and latency benchmarks before a reranker is introduced.

## First-Stage Retrieval

A reranker starts after first-stage retrieval. Elasticsearch retrieves a broad candidate set using lexical search, boosted lexical search, hybrid retrieval, or another high-recall strategy. This first stage should be fast and should avoid missing plausible products.

A common pattern is:

- Retrieve the top 100 candidates from Elasticsearch.
- Rerank only a smaller window, such as the top 20.
- Return the top 10 results to the user.

The candidate set needs to be large enough to include semantically relevant products, but not so large that reranking cost dominates the request.

## Rerank Window

The rerank window is the subset of candidates passed to the reranker. In this lab the default is a top-20 window. Products outside the window keep their first-stage order. This makes latency bounded and keeps the reranker focused on the results most likely to reach the first page.

## Why Reranking Can Help

A first-stage retriever is optimized for recall and speed. A reranker can spend more compute on a smaller set and use richer text matching, semantic similarity, cross-encoder scores, or marketplace-specific signals. That can improve nDCG@10 when the first-stage retriever found good candidates but ordered them poorly.

Reranking is especially useful when queries are vague, natural-language-like, or intent-heavy. It can help distinguish products that share keywords but differ in use case.

## Why Reranking Costs More

Reranking adds another step to the request path. Even a local placeholder has measurable overhead; a real model may add CPU, GPU, memory, network, or service cost. Reranking can also make p95 and p99 latency worse, which matters for search incidents and conversion-sensitive pages.

That is why reranking should be measured as a relevance and latency tradeoff, not treated as an automatic upgrade.

## Local Placeholder Reranker

`src/search/rerank.py` includes `PlaceholderTextSimilarityReranker`. It uses deterministic token overlap for demos and tests. It is deliberately labeled as a placeholder and does not pretend to be a real ML reranker.

The placeholder exists to show the workflow:

1. Retrieve candidates.
2. Rerank a bounded window.
3. Compare nDCG@10, MRR, and Precision@10 before and after.
4. Compare first-stage latency with total latency.
5. Warn when relevance improves but p95 latency worsens.

## Evaluation

Run the local reranking evaluation with:

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_reranking.py
```

To include hybrid retrieval as a first stage:

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_reranking.py --hybrid always
```

By default, the script includes hybrid retrieval when embeddings exist in the index. It writes `examples/reranking_report.md` and prints metric deltas and latency deltas. nDCG@10 is the most useful primary metric because reranking changes order and the judgments are graded.

## Wiring Elastic Semantic Reranking Later

A later version could replace the placeholder with Elastic semantic reranking or another model-backed reranker. The interface should stay stable:

```python
class Reranker:
    def rerank(query: str, candidates: list[SearchResult]) -> list[SearchResult]: ...
```

A production implementation would need model/version tracking, timeout budgets, fallback behavior, feature flags, latency dashboards, and offline plus online evaluation before becoming a default path.
