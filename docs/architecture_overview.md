# Architecture Overview

## Components

```mermaid
flowchart LR
    Raw["Raw datasets / JSONL samples"] --> ETL["Dataset ETL + synthetic events"]
    ETL --> Events["Source-owned events"]
    ETL --> Snapshots["Product snapshots"]
    Events --> State["Canonical source state"]
    Snapshots --> State
    State --> Builder["Canonical product builder"]
    Builder --> Staging["Versioned products-v{build_id}"]
    Staging --> Alias["products-read alias"]
    Alias --> API["Search API"]
    Live["products-live optional overlay"] --> API
    Suggest["product-suggest"] --> API
    Policies["Optional policy JSON / search-policies"] --> API
    API --> Eval["Evaluation + benchmark"]
```

The stable product-search index is built from complete canonical product documents. Source systems own fields separately: catalog, price, inventory, reviews, and analytics. The builder merges source state before indexing so Elasticsearch does not become the business-merge layer.

## Sequence

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant ETL as ETL / Replay
    participant Builder as Canonical Builder
    participant ES as Elasticsearch
    participant API as Search API

    Dev->>ETL: Generate snapshots or source events
    ETL->>Builder: Apply source-owned updates
    Builder-->>ETL: Complete indexable product document
    ETL->>ES: Bulk index to products-v{build_id}
    Dev->>ES: Switch products-read alias
    API->>ES: Search products-read
    API->>ES: Optional mget products-live
    API-->>Dev: Ranked results with optional overlays/debug
```

## Review Guide

- Ingestion contracts: `src/ingestion/canonical_types.py`, `src/ingestion/source_state.py`, `src/ingestion/canonical_builder.py`
- Kafka-compatible optional path: `src/ingestion/kafka_consumer.py`
- Versioned indexing and aliases: `src/search/index_management.py`
- API read path: `apps/api/src/search/*`
- Dataset adapters: `scripts/prepare_*_sample.py`
- Governance policies: `apps/api/src/search/policies.ts`

## What Stays Optional

Kafka, live overlays, suggest, dataset adapters, and governance policies are optional layers. The local JSONL path still works with Elasticsearch and small checked-in sample files.
