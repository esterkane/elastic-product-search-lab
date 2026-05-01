# Elasticsearch Product Search Lab

This project is a compact Elasticsearch product-search lab. It indexes product data, models product fields for search, supports keyword and hybrid retrieval, simulates catalog change events, and evaluates relevance with offline metrics such as nDCG@k, MRR, and Precision@k.

## Why This Project Exists

Product search sits at the intersection of search relevance, data modeling, ingestion reliability, and user intent. This lab exists to make those tradeoffs concrete in a small, inspectable codebase: the goal is to show how catalog data can be shaped for Elasticsearch, how retrieval strategies can be compared, and how relevance improvements can be measured instead of guessed.

The project is designed as a portfolio-grade search-engineering workspace. It favors clear architecture notes, reproducible local setup, and explicit evaluation practices over a thin demo UI.

## Architecture Overview

The planned system is organized around four search-engineering workflows:

1. **Catalog ingestion** reads product records, normalizes fields, validates required attributes, and writes product documents to Elasticsearch.
2. **Index modeling** defines mappings, analyzers, multilingual fields, ranking signals, and index-versioning conventions.
3. **Retrieval** supports keyword search first, then hybrid retrieval that combines lexical matching with vector similarity.
4. **Evaluation** runs offline query sets against expected judgments and reports nDCG@k, MRR, Precision@k, and failure cases.

```text
sample product data -> ingestion pipeline -> Elasticsearch index
                                      |             |
                                      v             v
                              change events   search API / experiments
                                                    |
                                                    v
                                           offline relevance reports
```

## Planned Features

- Local Elasticsearch and Kibana stack with Docker Compose.
- Product index mappings for titles, descriptions, brands, categories, attributes, prices, availability, and behavioral ranking signals.
- Keyword retrieval with analyzers, boosts, filters, facets, and sorting.
- Hybrid retrieval experiments using embeddings and vector search.
- Catalog change simulation for creates, updates, deletes, price changes, and availability changes.
- Offline relevance evaluation with query fixtures and graded judgments.
- Example reports comparing keyword and hybrid strategies.
- API layer for search experiments and repeatable evaluation runs.

## Prerequisites

- Docker Desktop with enough memory allocated for a 6 GB Elasticsearch heap.
- PowerShell 5.1 or newer.
- Git for version control.

Optional for later implementation work:

- Node.js and npm for the planned API and search experiments.
- Python and pip for the planned ingestion and relevance evaluation utilities.

## Start Elasticsearch and Kibana

From the repository root, start the local single-node Elasticsearch runtime and Kibana:

```powershell
.\scripts\dev-up.ps1
```

The script uses `ELASTIC_VERSION` when it is set, otherwise it defaults to Elasticsearch and Kibana `9.3.0` through Docker Compose.

## Verify Elasticsearch and Kibana Are Reachable

Check the local Elasticsearch cluster health endpoint and Kibana status endpoint:

```powershell
.\scripts\check-es.ps1
.\scripts\check-kibana.ps1
```

You can also call the services directly:

```powershell
Invoke-RestMethod http://localhost:9200
Invoke-RestMethod http://localhost:9200/_cluster/health
Invoke-RestMethod http://localhost:5601/api/status
```

Kibana is available in the browser at `http://localhost:5601`.

## Stop Elasticsearch and Kibana

Stop the local runtime while keeping the named Elasticsearch Docker volume:

```powershell
.\scripts\dev-down.ps1
```

To remove the persisted local Elasticsearch data as well, run Docker Compose manually with the volume flag:

```powershell
docker compose down -v
```

## Quickstart

The first local runtime is available through Docker Compose. The intended development flow is:

```powershell
.\scripts\dev-up.ps1
.\scripts\check-es.ps1
.\scripts\check-kibana.ps1
# install API and Python dependencies as implementation lands
# load sample products
# run search examples
# run relevance evaluation
.\scripts\dev-down.ps1
```

## Relevance Evaluation

The evaluation module will compare retrieval strategies against curated query judgments. Planned metrics include:

- nDCG@k for graded relevance quality.
- MRR for first-good-result behavior.
- Precision@k for top-result concentration.
- Query-level diagnostics for regressions and mapping failures.

## Ingestion Simulation

The ingestion workflow will include repeatable scripts that simulate catalog lifecycle events:

- New product creation.
- Product title, category, and attribute updates.
- Price and promotion updates.
- Stock and availability changes.
- Product deletion or deactivation.

## Tech Stack

- Elasticsearch 9.3.0
- Kibana 9.3.0
- Docker Compose
- Node.js / TypeScript for API and search experiments
- Python for ingestion, evaluation, and analysis utilities
- GitHub Actions planned for validation once implementation begins

## Roadmap

- [x] Add Docker Compose Elasticsearch service and health checks.
- [x] Add Kibana to the local development runtime.
- [ ] Define product mappings and analyzer strategy.
- [ ] Add sample product catalog fixtures.
- [ ] Implement ingestion scripts.
- [ ] Implement keyword search API.
- [ ] Add hybrid retrieval experiments.
- [ ] Build offline relevance evaluation fixtures and reports.
- [ ] Add performance and resilience notes from local experiments.

## Portfolio Note

This is an educational/search-engineering lab, not a production marketplace backend. It is intentionally compact so the search architecture, relevance decisions, and evaluation workflow remain easy to inspect.
