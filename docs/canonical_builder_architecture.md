# Canonical Product Builder Architecture

## Goal

This phase introduces a canonical product document layer before Elasticsearch indexing. The product-search index should receive complete, deterministic product documents assembled from source-owned state instead of becoming the place where many independent partial updaters merge business fields.

The existing JSONL sample loader and product event replay remain available. The new canonical builder is a small Python interface that batch jobs, replay workers, or a later Kafka consumer can call before indexing.

## Current Components

| Component | Current role | Canonical architecture role |
| --- | --- | --- |
| `data/sample/products.jsonl` | Complete sample product records for local indexing. | Treated as complete source snapshots and translated into source-owned state. |
| `scripts/load_sample_data.py` | Loads sample products and bulk indexes them. | Still loads JSONL; `Product.to_index_document()` now emits through the canonical builder. |
| `src/ingestion/models.py` | Validates complete product rows and builds index documents. | Keeps the public model while delegating final document assembly to `canonical_builder`. |
| `src/ingestion/search_profile.py` | Derives deterministic product retrieval text. | Called by the canonical builder for the final `search_profile`. |
| `src/ingestion/bulk_indexer.py` | Builds Elasticsearch bulk operations. | Continues indexing complete documents only. |
| `data/sample/product_events.jsonl` | Deterministic event replay fixture. | Still used by the existing replay path. Future replay can update `ProductSourceState` first. |
| `src/ingestion/product_event_consumer.py` | Applies direct partial updates into Elasticsearch. | Preserved for backward compatibility during phase 1; not expanded. |
| `src/search/product_mapping.json` | Strict mapping for `products-v1`. | Remains the target schema for emitted canonical documents. |
| `apps/api/src/search/*` and `apps/api/src/routes/search.ts` | Search API over the product index. | No change; it reads the final searchable product index. |

## Source Ownership

The canonical layer models ownership explicitly:

| Source | Owned fields |
| --- | --- |
| `catalog` | `title`, `description`, `brand`, `category`, `attributes`, `seller_id` |
| `price` | `price`, `currency` |
| `inventory` | `availability` |
| `reviews` | `average_rating`, `review_count` |
| `analytics` | `popularity_score` |

Each `SourceUpdate` carries `product_id`, `source`, `source_version`, optional `updated_at`, and source-owned `fields`. `ProductSourceState.apply()` rejects updates that try to write fields outside the source ownership table. That keeps unrelated fields from being overwritten by the wrong producer.

## Assembly Flow

```mermaid
flowchart LR
    A["Source snapshots or events"] --> B["SourceUpdate"]
    B --> C["ProductSourceState"]
    C --> D["Canonical builder"]
    D --> E["Complete product document"]
    E --> F["Bulk indexer"]
    F --> G["products-v1 Elasticsearch index"]
```

The builder emits only when minimum searchable fields exist:

- `product_id`
- `title`
- `brand`
- `category`
- `price`
- `currency`
- `availability`
- `seller_id`

If any required field is missing, the builder returns a structured `CanonicalBuildResult` with `emitted=false` and a `canonical_product_incomplete` issue marked `retryable=true`. A future Kafka consumer can keep or retry that product state until the missing source arrives.

## Source Clocks

`source_versions` stores the latest accepted version per source. Numeric clocks compare numerically; non-numeric clocks compare as strings. The sample JSONL path also preserves the historical `sample_jsonl` version key for compatibility while adding canonical source clocks for `catalog`, `price`, `inventory`, and `analytics`.

## Elasticsearch Boundary

Canonical assembly stays in application code. Elasticsearch ingest pipelines should remain minimal and last-mile only, for example for operational metadata that does not require cross-source product semantics. The `products-v1` mapping remains strict, so phase 1 does not emit review fields into Elasticsearch until the mapping and search API intentionally add them.

## Kafka-Ready Interface

Future Kafka consumers can call the same pure interface used by tests:

```python
state.apply(SourceUpdate(...))
result = build_canonical_product_document(state)
if result.emitted:
    client.index(index="products-v1", id=result.product_id, document=result.document)
```

In a production worker, `ProductSourceState` would be stored in a durable state store keyed by `product_id`; Kafka partitions should preserve per-product ordering where possible. Non-retryable validation errors are rejected immediately by `SourceUpdate` or ownership checks. Retryable incomplete-product results should be retained until missing source data arrives.
