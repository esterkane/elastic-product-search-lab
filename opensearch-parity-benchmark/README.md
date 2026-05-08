# OpenSearch Parity Benchmark

This is a small OpenSearch-native benchmark for a retrieval portfolio. It demonstrates a lexical BM25 baseline and a hybrid retrieval strategy that uses OpenSearch's `hybrid` query plus an RRF search pipeline.

The corpus is intentionally tiny and deterministic: 12 synthetic product-support documents with judged relevance labels for four queries. Embeddings are local hash vectors, not a model-quality claim. The point is to prove OpenSearch plumbing, evaluation discipline, and benchmark reproducibility.

## What It Uses

- OpenSearch `2.19.1`
- BM25 via `multi_match`
- Raw vector retrieval via `knn_vector` and `knn`
- Native hybrid query with multiple query clauses
- Native RRF through `score-ranker-processor`
- Judged metrics: nDCG@10, Precision@5, MRR@10, Recall@10, p50/p95 latency

The RRF path follows OpenSearch's native search-pipeline shape:

```json
{
  "phase_results_processors": [
    {
      "score-ranker-processor": {
        "combination": {
          "technique": "rrf",
          "rank_constant": 60
        }
      }
    }
  ]
}
```

Reference docs:

- [OpenSearch hybrid search](https://docs.opensearch.org/docs/3.0/vector-search/ai-search/hybrid-search/index/)
- [OpenSearch score ranker processor](https://docs.opensearch.org/latest/search-plugins/search-pipelines/score-ranker-processor/)
- [OpenSearch Docker install](https://docs.opensearch.org/latest/install-and-configure/install-opensearch/docker/)

## Run

From this directory:

```powershell
docker compose up -d
python scripts/run_benchmark.py
```

If `python` is not on PATH, use an explicit Python executable:

```powershell
C:\path\to\python.exe scripts\run_benchmark.py
```

Outputs:

- `reports/opensearch-parity-report.json`
- `reports/opensearch-parity-report.md`

## Verify Manually

Health:

```powershell
curl http://localhost:9201/_cluster/health
```

Index:

```powershell
curl http://localhost:9201/product_support_docs/_count
```

Pipeline:

```powershell
curl http://localhost:9201/_search/pipeline/product-support-rrf
```

Hybrid search:

```powershell
curl -X POST "http://localhost:9201/product_support_docs/_search?search_pipeline=product-support-rrf" -H "Content-Type: application/json" -d "{\"size\":3,\"query\":{\"hybrid\":{\"queries\":[{\"multi_match\":{\"query\":\"usb c laptop backpack warranty\",\"fields\":[\"title^3\",\"body\"]}},{\"knn\":{\"embedding\":{\"vector\":[0.0,0.0,0.0,0.408248,0.408248,0.408248,0.0,-0.408248,0.0,0.0,0.408248,0.0,0.0,0.0,0.0,0.408248],\"k\":3}}}]}}}"
```

## OpenSearch vs Elasticsearch Notes

- OpenSearch hybrid retrieval is expressed through a `hybrid` query and search pipelines. Elasticsearch commonly uses `retriever.rrf` in the search request for comparable rank fusion.
- OpenSearch RRF is configured by the `score-ranker-processor` in a search pipeline. That makes the RRF choice reusable across requests, but it also means the benchmark needs pipeline setup before evaluation.
- This benchmark uses raw vectors to avoid an external ML model dependency. A production semantic path would replace deterministic hash vectors with model-generated embeddings or OpenSearch neural search model registration.

## Limitations

- The corpus is synthetic and small, so the metrics are a wiring check, not a statistically meaningful relevance study.
- Latency numbers are local Docker timings and should be compared only within the same machine/run context.
- No frontend is included; this is intentionally an API and evaluation artifact.

## Cleanup

```powershell
docker compose down
```
