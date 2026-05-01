# Application Facts: Senior Search Engineer - Elasticsearch

## Role Alignment Summary

I bring nearly 5 years of deep Elasticsearch production support experience at Elastic, 12+ years in technical support/application engineering, and practical search/AI project work focused on relevance, diagnostics, retrieval, and knowledge systems.

This page summarizes the evidence behind that alignment. It is intentionally factual: this repository is a search-engineering lab, not a claim of having spent 7+ years as a dedicated product Search Engineer.

| Target role need | My evidence | Repo evidence |
| --- | --- | --- |
| Improve product search relevance | Production Elasticsearch troubleshooting experience, relevance-focused project work, and practical evaluation habits | BM25 query tuning, hybrid search experiments, reranking workflow, and offline nDCG/MRR/Precision reports |
| Diagnose search and indexing issues | Nearly 5 years supporting Elasticsearch production cases at Elastic | Explicit mappings, create-index script, ingestion validation, bulk indexing summaries, and event replay behavior |
| Model product data for search | Application engineering background plus Elasticsearch mapping and ingest experience | Product schema, `flattened` attributes, keyword/text fields, scaled prices, timestamps, source versions, and dense vectors |
| Handle catalog updates safely | Support experience with production failure modes and replay/idempotency thinking | Deterministic `_id = product_id`, stale event protection, source-version tracking, and update-vs-upsert documentation |
| Measure success and failure | Evidence-based troubleshooting and clear written communication | Relevance reports, performance reports, benchmark summaries, CI tests, and documented tradeoffs |
| Improve performance and resilience | Production diagnostics mindset around latency, errors, timeouts, and backpressure | p50/p95/p99 benchmark, API timeout handling, safe errors, bulk retry/backoff, and resilience notes |
| Work across support, engineering, documentation, and product thinking | 12+ years in technical support/application engineering and nearly 5 years in Elastic support | Portfolio-ready README, architecture docs, mapping decisions, ingestion docs, and role-alignment evidence |
| Explore AI/search tooling | Practical work with RAG, hybrid retrieval, embeddings, and knowledge workflows | Optional local embeddings, RRF fusion, semantic/hybrid docs, placeholder reranking, and future `semantic_text` roadmap |

## Evidence From Current Experience

- Nearly 5 years of Elasticsearch production support experience at Elastic.
- 12+ years across technical support and application engineering.
- Daily work style built around reproducible diagnostics, log and metric evidence, clear written communication, and customer-safe explanations.
- Practical bridge between support, engineering, documentation, product feedback, and knowledge reuse.
- Current focus on AI-assisted support workflows, retrieval quality, search diagnostics, and technical knowledge systems.

## Evidence From This Repository

This repository demonstrates applied search-engineering thinking in a compact local lab:

- Elasticsearch mappings for product search fields, facets, source versions, timestamps, and dense vectors.
- Deterministic product ingestion using `_id = product_id`.
- Bulk indexing with validation, retries, exponential backoff, and jitter.
- Simulated catalog change events from multiple source systems into one product document.
- TypeScript/Node.js Fastify API with query validation, safe backend errors, request timeout configuration, and route tests.
- Offline relevance metrics and reports.
- Local search latency benchmarks.
- Optional hybrid search and reranking workflows.
- GitHub Actions CI for API and Python unit tests.

## Search Relevance and Metrics

The repository treats relevance as something to measure, not guess. It includes:

- BM25 `multi_match` query over title, brand, category, description, and combined catalog text.
- Field boosts that make title matches more important than broad description matches.
- Filter context for category, brand, availability, and price constraints.
- Mild popularity and recency boosts with documentation about why over-weighting them can hurt niche exact matches.
- Offline metrics: Precision@10, MRR, DCG, and nDCG@10.
- Per-query reporting so aggregate gains do not hide regressions.

## Ingestion and Data Modelling

The ingestion design is intentionally deterministic and replay-friendly:

- Product records are validated with Pydantic before indexing.
- Bulk indexing uses stable document IDs derived from `product_id`.
- Change events update existing product documents instead of creating duplicates.
- `source_versions[source_system]` protects against stale out-of-order events.
- Partial updates are documented separately from full index operations and `doc_as_upsert` behavior.
- Product mappings separate searchable text, filterable keywords, flexible attributes, prices, availability, timestamps, and vector fields.

## Performance and Resilience

The project includes local resilience patterns that map to production thinking:

- Bulk retries use exponential backoff with jitter for transient `429`, `503`, and connection failures.
- Validation and mapping errors are not retried forever.
- API Elasticsearch calls use request timeout configuration.
- API errors are sanitized so stack traces and backend details are not exposed to clients.
- Benchmarks report p50, p95, p99, min, max, error rate, and timeout rate.
- Documentation distinguishes alerts that should page from signals that should remain dashboard-only.

## Search/AI Roadmap Readiness

The repository is ready for deeper search/AI extensions without making them mandatory for the MVP:

- Optional local dense embeddings with a 384-dimensional model path.
- RRF-style hybrid search combining lexical and vector retrieval.
- Optional reranking interface with a clearly marked deterministic placeholder.
- ESCI dataset preparation path for a real public product-search relevance dataset.
- Roadmap ideas for Kafka or Redpanda, gRPC, React dashboards, Elasticsearch `rank_eval`, `semantic_text`, and observability dashboard mapping.

## Honest Gap Statement

I am not presenting myself as someone with 7+ years in a dedicated product Search Engineer title. My strongest foundation is nearly 5 years of deep Elasticsearch production support experience at Elastic, plus 12+ years of broader technical support/application engineering and hands-on search/AI project work.

The value I bring is the combination: production troubleshooting discipline, Elasticsearch depth, clear communication, support-to-engineering bridge work, and practical search relevance projects that show I can reason about mappings, ingestion, ranking, evaluation, latency, and resilience together.