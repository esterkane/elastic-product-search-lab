# Ingestion Architecture

The ingestion pipeline turns product catalog records and catalog change events into deterministic Elasticsearch documents. The local implementation uses `data/sample/products.jsonl`; the same stages can later read Amazon ESCI product parquet rows and normalize them into the lab product schema.

Phase 1 adds a canonical product document builder before Elasticsearch indexing. The main product-search index should receive complete product documents assembled from source-owned state, not rely on Elasticsearch to merge many business-field partial updates.

## What To Review First

- `src/ingestion/models.py` validates product records before indexing.
- `src/ingestion/canonical_types.py` defines source ownership and canonical build result types.
- `src/ingestion/source_state.py` keeps latest source-owned product state and source clocks.
- `src/ingestion/canonical_builder.py` emits complete searchable documents, `catalog_text`, and `search_profile`.
- `src/ingestion/bulk_indexer.py` writes deterministic documents with bounded retries.
- `src/ingestion/product_event_consumer.py` preserves the existing JSONL direct partial-update replay path.
- `data/sample/product_events.jsonl` shows multiple source systems updating one document.
- `docs/canonical_builder_architecture.md` explains the Kaufland-style canonical assembly boundary.

## Deterministic Product IDs

Every Elasticsearch write uses `_id = product_id`. That makes indexing idempotent: replaying the same product record updates the same document instead of creating duplicates. Deterministic IDs also make debugging easier because the source catalog identifier and Elasticsearch document identifier are the same.

## Why Idempotency Matters

Real catalog pipelines replay data during recovery, backfills, and reindexing. If the write path is not idempotent, a retry can duplicate products and distort relevance evaluation. With deterministic IDs, repeated writes converge on one document per product.

## Canonical Assembly Flow

The canonical layer separates source ownership from final index shape:

1. Upstream snapshots or events are represented as `SourceUpdate`.
2. `ProductSourceState.apply()` accepts only fields owned by that source.
3. Newer source versions replace older state for that source only.
4. `build_canonical_product_document()` merges source-owned state.
5. Incomplete products return a structured retryable issue instead of becoming searchable documents.
6. Complete products emit the strict `products-v1` document shape with `source_versions`, `catalog_text`, and `search_profile`.

The current source ownership table is:

| Source | Owned fields |
| --- | --- |
| `catalog` | `title`, `description`, `brand`, `category`, `attributes`, `seller_id` |
| `price` | `price`, `currency` |
| `inventory` | `availability` |
| `reviews` | `average_rating`, `review_count` |
| `analytics` | `popularity_score` |

Review fields are modeled for ownership but are not emitted to `products-v1` yet because the current mapping is strict and does not include them.

## Bulk Indexing Flow

The local loader follows a small but production-shaped flow:

1. Ensure the product index exists.
2. Validate JSONL records with a Pydantic product model.
3. Translate complete sample rows into source-owned canonical state.
4. Build complete index documents with deterministic document IDs.
5. Send batches through the Elasticsearch bulk API.
6. Retry only transient failures such as `429`, `503`, or connection errors.
7. Refresh the index for local demo visibility.
8. Print indexed, failed, retry, and elapsed-time summary values.

## Backoff Instead of Crash Loops

Bulk indexing can create pressure on Elasticsearch thread pools, queues, heap, and disk. Immediate retry loops make overload worse. The indexer uses exponential backoff with jitter for transient failures so multiple workers do not retry in lockstep and amplify an incident.

Validation and mapping errors are different. A malformed document or incompatible field type will not become valid by retrying forever, so those failures are logged and counted instead of retried indefinitely.

## Kafka-Style Offset Discipline

When this lab grows into an event-driven ingestion design, Kafka offsets should only be committed after Elasticsearch accepts the write or the event is explicitly classified as stale. Committing before the write risks losing catalog updates if the worker crashes between the offset commit and the Elasticsearch response. Accepting occasional replay is safer because deterministic product IDs and source versions make replay idempotent.

## Simulated Catalog Change Events

The event replay path shows how one upstream change becomes one deterministic Elasticsearch document update. Each event carries an `event_id`, `product_id`, `source_system`, `event_type`, `event_time`, `payload`, and numeric `source_version`. The consumer always targets `_id = product_id`, so a title, price, availability, category, seller, attribute, or delete/unavailable event updates the same document that bulk ingestion created.

`updated_at` comes from the business event time because search freshness should reflect when the catalog state changed. `indexed_at` comes from the ingestion worker time because operators need to measure pipeline lag separately from business time.

This direct partial-update replay path is intentionally preserved for backward compatibility. Future Kafka or replay consumers should use the canonical interface instead: apply the source event to durable `ProductSourceState`, build the complete canonical document, and then index that document into Elasticsearch.

## Index, Update, Upsert, and Scripted Updates

A full product snapshot should use an index operation because the incoming record owns the complete searchable document. A partial catalog event should use an update operation because it only owns a few fields. `doc_as_upsert` is intentionally not used for the current simulated events: a price-only or availability-only event cannot safely create a complete searchable product.

`doc_as_upsert` becomes appropriate only when the event payload is a complete product snapshot or when the consumer can hydrate missing fields from a trusted product store before writing. Scripted updates are useful when Elasticsearch must merge nested state atomically, increment counters, or guard on values inside the document. This lab performs the merge in Python for readability: it reads `source_versions`, checks freshness, then writes a merged partial document with `retry_on_conflict` enabled.

## Multi-Source Updates Into One Document

Product search documents are assembled from multiple source systems. In the canonical builder, `catalog` owns title, description, brand, category, attributes, and seller identity; `inventory` owns availability; `price` owns price and currency; `analytics` owns popularity features; and `reviews` owns future review aggregates. The `source_versions` map records the latest accepted version per source so one source can update its fields without erasing another source's progress.

## Stale Event Protection

Distributed catalog systems can deliver events out of order. For example, inventory version 88 may mark a product as `limited_stock`, and version 80 may arrive later from a delayed partition. Without stale protection, the older event could incorrectly restore `in_stock`. The consumer compares the event's `source_version` against `source_versions[source_system]` and skips older or equal versions.

The local sample file includes this case so the replay command demonstrates both accepted updates and a skipped stale event.

## ESCI Dataset Path

The Amazon ESCI dataset is useful for relevance experiments because it includes query-product judgments and product metadata. The first ingestion step should load unique product rows from `shopping_queries_dataset_products.parquet`, normalize them into this schema, and keep query judgments for evaluation rather than mixing them into product documents.
