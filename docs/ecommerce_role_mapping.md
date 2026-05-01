# E-commerce Search Role Mapping

This document maps the lab to common product-search engineering expectations. It is honest by design: the repo is a local lab, not a production marketplace, but it demonstrates practical search-engineering thinking in executable form.

| E-commerce search expectation | Where this repo demonstrates it | Evidence |
| --- | --- | --- |
| Improve relevance | BM25 tuning, hybrid search, reranking workflow, and offline judgments | `docs/relevance_strategy.md`, `scripts/evaluate_search.py`, `scripts/evaluate_hybrid_search.py`, `scripts/evaluate_reranking.py` |
| Faster queries | Local latency benchmark with p50, p95, p99, error rate, and timeout rate | `scripts/benchmark_search.py`, `examples/performance_report.md` |
| Improve ingested data quality | Pydantic product validation, deterministic bulk indexing, and ESCI sample preparation | `src/ingestion/models.py`, `src/ingestion/bulk_indexer.py`, `scripts/prepare_esci_sample.py` |
| Update mappings and index new fields | Explicit Elasticsearch mapping with product fields, source versions, timestamps, and vectors | `src/search/product_mapping.json`, `scripts/create_index.py`, `docs/mapping_decisions.md` |
| Single document from multiple sources | Event replay updates one product document from content, category, inventory, pricing, and seller sources | `src/ingestion/product_event_consumer.py`, `data/sample/product_events.jsonl` |
| Data modelling | Product schema separates searchable text, filter fields, attributes, prices, availability, and embeddings | `src/ingestion/models.py`, `docs/mapping_decisions.md` |
| Performance enhancement | Benchmark compares baseline lexical, boosted lexical, and hybrid strategies | `scripts/benchmark_search.py`, `docs/performance_and_resilience.md` |
| Safety/resilience | Retries use exponential backoff with jitter; API uses timeouts and sanitized errors | `src/ingestion/bulk_indexer.py`, `apps/api/src/app.ts`, `apps/api/src/elasticsearch.ts` |
| Metrics of success/failure | Relevance and latency reports expose per-query and aggregate results | `examples/relevance_report.md`, `examples/performance_report.md`, `examples/reranking_report.md` |
| Semantic/hybrid/vector search curiosity | Optional local embeddings, dense vectors, RRF fusion, and reranking docs | `src/embeddings/embedder.py`, `src/search/hybrid_search.py`, `docs/hybrid_search.md`, `docs/reranking.md` |
| TypeScript/Node.js | Fastify API with query validation, Elasticsearch client, route tests, and safe error handling | `apps/api/src`, `apps/api/tests` |
| Kafka-style event thinking | Event model tracks source systems, source versions, stale events, and offset discipline in docs | `src/ingestion/events.py`, `src/ingestion/product_event_consumer.py`, `docs/ingestion_architecture.md` |
