# Implementation Plan

## Inspection Summary

### Current backend/API stack

- `apps/api` is a TypeScript/Node.js Fastify API.
- It uses the official `@elastic/elasticsearch` JavaScript client.
- Main API files:
  - `apps/api/src/app.ts`
  - `apps/api/src/server.ts`
  - `apps/api/src/routes/search.ts`
  - `apps/api/src/routes/product.ts`
  - `apps/api/src/routes/health.ts`
  - `apps/api/src/search/queryBuilder.ts`
  - `apps/api/src/search/searchClient.ts`
- API scripts already exist in `apps/api/package.json`:
  - `npm run dev`
  - `npm run build`
  - `npm run test`
  - `npm run lint`

### Current ingestion scripts

- Product bulk ingestion exists in Python:
  - `src/ingestion/models.py`
  - `src/ingestion/bulk_indexer.py`
  - `scripts/load_sample_data.py`
- Catalog change/event ingestion exists:
  - `src/ingestion/events.py`
  - `src/ingestion/product_event_consumer.py`
  - `scripts/replay_product_events.py`
- Optional ESCI sample preparation exists:
  - `scripts/prepare_esci_sample.py`

### Current Elasticsearch mapping/index setup

- Mapping is explicit and production-inspired:
  - `src/search/product_mapping.json`
- Index creation is scripted:
  - `scripts/create_index.py`
- Local runtime is Docker Compose based:
  - `docker-compose.yml`
  - Elasticsearch 9.3.0 by default
  - Kibana 9.3.0 by default
- Mapping includes keyword/text fields, `flattened` attributes, scaled price, timestamps, `source_versions`, and a 384-dimensional indexed `dense_vector` field.

### Current sample data format

- Main product sample data is JSONL:
  - `data/sample/products.jsonl`
- Each product includes:
  - `product_id`
  - `title`
  - `description`
  - `brand`
  - `category`
  - `attributes`
  - `price`
  - `currency`
  - `availability`
  - `popularity_score`
  - `seller_id`
  - `updated_at`
- Relevance judgments are JSONL:
  - `data/sample/judgments.jsonl`
- Catalog events are JSONL:
  - `data/sample/product_events.jsonl`
- Optional ESCI sample files exist:
  - `data/sample/esci_sample_products.jsonl`
  - `data/sample/esci_sample_judgments.jsonl`

### Existing search strategies

- API query builder supports:
  - baseline BM25-style `multi_match`
  - boosted query via `function_score`
  - filters for category, brand, availability, and price range
  - debug output with query DSL
- Python search experiments include:
  - baseline lexical search
  - boosted lexical search
  - optional kNN/vector search
  - local RRF fusion
  - optional placeholder reranking workflow
- Relevant files:
  - `apps/api/src/search/queryBuilder.ts`
  - `src/search/hybrid_search.py`
  - `src/search/rerank.py`
  - `scripts/evaluate_hybrid_search.py`
  - `scripts/evaluate_reranking.py`

### Existing evaluation or benchmark scripts

- Judgment-list relevance evaluation exists:
  - `scripts/evaluate_search.py`
  - `src/evaluation/metrics.py`
  - `src/evaluation/judgments.py`
- Hybrid strategy comparison exists:
  - `scripts/evaluate_hybrid_search.py`
- Reranking evaluation exists:
  - `scripts/evaluate_reranking.py`
- Latency benchmark exists:
  - `scripts/benchmark_search.py`
- Generated Markdown reports already exist:
  - `examples/relevance_report.md`
  - `examples/performance_report.md`
  - `examples/reranking_report.md`

### Existing tests and CI config

- Python tests live in `tests/python` and cover mapping, ingestion, events, metrics, ESCI prep, hybrid search, benchmark summary, and reranking.
- API tests live in `apps/api/tests` and cover health, query builder, and search route behavior.
- CI exists in `.github/workflows/ci.yml` and runs:
  - Node.js LTS setup
  - `npm ci`
  - `npm test`
  - `npm run build`
  - Python 3.12 setup
  - `python -m pip install -e .`
  - `python -m pytest tests/python -m "not integration"`

## What Already Exists

The repo already has the core pieces needed for a compact e-commerce product search relevance lab:

- Local Elasticsearch and Kibana runtime.
- Explicit product index mappings.
- Deterministic product ingestion.
- Simulated catalog update events.
- Judgment-list based relevance evaluation.
- Baseline, boosted, hybrid, and reranking search experiments.
- Latency benchmark with p50/p95/p99 and error/timeout rates.
- Generated Markdown reports.
- TypeScript app-facing API.
- Python ingestion and evaluation utilities.
- Unit tests and GitHub Actions CI.

## What Needs To Be Added

Keep the next implementation small. The repo does not need a rewrite. The highest-value next step is to make measurable improvement easier to demonstrate from one command and one README section.

Recommended scope for today:

1. Add one consolidated comparison report script.
   - Compare baseline lexical vs boosted lexical vs optional hybrid.
   - Use the existing judgment list.
   - Include nDCG@10, MRR, Precision@10, and latency columns.
   - Write one Markdown report that a reviewer can read quickly.

2. Add a small README facts-and-figures section.
   - Include current sample data size.
   - Include current relevance metrics from `examples/relevance_report.md`.
   - Include current latency metrics from `examples/performance_report.md`.
   - Link to the generated reports.

3. Add tests for the consolidated report logic.
   - Do not require Elasticsearch in CI.
   - Unit-test metric delta and Markdown table generation with fixed inputs.

4. Optionally mark any future live-Elasticsearch tests with `@pytest.mark.integration`.
   - CI should continue excluding integration tests by default.

## Files To Modify

Suggested files for the next small implementation:

- `scripts/compare_search_strategies.py` - new consolidated report runner.
- `src/evaluation/reporting.py` - optional small helper for Markdown table/report generation.
- `tests/python/test_strategy_report.py` - unit tests for delta/report generation.
- `examples/search_strategy_report.md` - generated reviewer-facing comparison report.
- `README.md` - add a short facts-and-figures section with links to reports.

Files to avoid rewriting unless there is a specific bug:

- `src/ingestion/*` - ingestion is already working and tested.
- `src/search/product_mapping.json` - mapping changes require reindexing and should be deliberate.
- `apps/api/src/*` - API already demonstrates the app-facing layer; new app-facing work should extend it, not replace it.

## Commands To Run Locally

Unit checks:

```powershell
cd C:\Users\sruzi\projects\elastic-product-search-lab
cd apps\api
npm test
npm run build
cd ..\..
.\.venv\Scripts\python.exe -m pytest tests/python
```

Local Elasticsearch demo:

```powershell
docker compose up -d
.\.venv\Scripts\python.exe scripts\create_index.py --recreate
.\.venv\Scripts\python.exe scripts\load_sample_data.py
.\.venv\Scripts\python.exe scripts\evaluate_search.py
.\.venv\Scripts\python.exe scripts\benchmark_search.py
docker compose down
```

Optional hybrid path:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[vector]"
.\.venv\Scripts\python.exe scripts\generate_embeddings.py --input data\sample\products.jsonl
.\.venv\Scripts\python.exe scripts\evaluate_hybrid_search.py
```

## Risks Or Assumptions

- Local Elasticsearch requires Docker Desktop and enough memory for the configured 6 GB heap.
- CI intentionally does not run live Elasticsearch integration tests.
- The sample catalog is small, so metrics are useful for demonstrating workflow, not for proving production-quality relevance.
- Hybrid and reranking paths are optional and should not become mandatory for the MVP.
- The current placeholder reranker is not an ML reranker and should remain labeled as such.
- Mapping changes require reindexing and should be avoided unless the next feature clearly needs them.
- If the next goal is application-facing polish, prefer TypeScript/Node.js additions around the existing Fastify API. Do not rewrite the working Python ingestion and evaluation scripts unless there is a specific reason.