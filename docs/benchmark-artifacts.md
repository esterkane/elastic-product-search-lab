# Benchmark Artifacts In CI

The `Benchmark Artifacts` workflow publishes the repository's lightweight relevance and latency reports as a single downloadable GitHub Actions artifact named `benchmark-review-reports`.

It regenerates reports that do not require external services:

- `reports/search-quality-report.json`
- `reports/search-quality-decision.md`
- `reranker-ablation-benchmark/reports/reranker-ablation-report.json`
- `reranker-ablation-benchmark/reports/reranker-ablation-report.md`
- `ingestion-sensitivity-experiment/reports/ingestion-sensitivity-report.json`
- `ingestion-sensitivity-experiment/reports/ingestion-sensitivity-report.md`
- `hybrid-explain-report/reports/hybrid-explain-report.json`
- `hybrid-explain-report/reports/hybrid-explain-report.md`
- `elastic-ai-search-decision-lab/reports/conversation-eval-report.json`
- `elastic-ai-search-decision-lab/reports/conversation-eval-report.md`

It also uploads the checked-in OpenSearch parity report without booting Docker:

- `opensearch-parity-benchmark/reports/opensearch-parity-report.json`
- `opensearch-parity-benchmark/reports/opensearch-parity-report.md`

## Local Reproduction

```powershell
python scripts/search_quality_program.py
cd reranker-ablation-benchmark; python scripts/reranker_ablation.py; cd ..
cd ingestion-sensitivity-experiment; python scripts/ingestion_sensitivity.py; cd ..
cd hybrid-explain-report; python scripts/generate_hybrid_explain.py; cd ..
cd elastic-ai-search-decision-lab; node src/evaluate.ts; cd ..
```

Run the OpenSearch parity benchmark locally only when Docker is available:

```powershell
cd opensearch-parity-benchmark
docker compose up -d
python scripts/run_benchmark.py
docker compose down
```
