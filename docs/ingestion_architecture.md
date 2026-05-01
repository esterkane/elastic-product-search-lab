# Ingestion Architecture

The ingestion pipeline turns product catalog records into deterministic Elasticsearch documents. The local implementation uses `data/sample/products.jsonl`; the same stages can later read Amazon ESCI product parquet rows from `shopping_queries_dataset_products.parquet` and map ESCI fields such as `product_title`, `product_description`, `product_brand`, `product_color`, and `product_locale` into the lab product schema.

## Deterministic Product IDs

Every Elasticsearch write uses `_id = product_id`. That makes indexing idempotent: replaying the same product record updates the same document instead of creating duplicates. Deterministic IDs also make debugging easier because the source catalog identifier and Elasticsearch document identifier are the same.

## Why Idempotency Matters

Real catalog pipelines replay data during recovery, backfills, and reindexing. If the write path is not idempotent, a retry can inflate inventory, duplicate products, and distort relevance evaluation. With deterministic IDs, repeated writes converge on one document per product.

## Bulk Indexing Flow

The local loader follows a small but production-shaped flow:

1. Ensure the product index exists.
2. Validate JSONL records with a Pydantic product model.
3. Build bulk index operations with deterministic document IDs.
4. Send batches through the Elasticsearch bulk API.
5. Retry only transient failures such as `429`, `503`, or connection errors.
6. Refresh the index for local demo visibility.
7. Print indexed, failed, retry, and elapsed-time summary values.

## Backoff Instead of Crash Loops

Bulk indexing can create pressure on Elasticsearch thread pools, queues, heap, and disk. Immediate retry loops make overload worse. The indexer uses exponential backoff with jitter for transient failures so multiple workers do not retry in lockstep and amplify an incident.

Validation and mapping errors are different. A malformed document or incompatible field type will not become valid by retrying forever, so those failures are logged and counted instead of retried indefinitely.

## Kafka Offset Discipline

When this lab grows into an event-driven ingestion design, Kafka offsets should only be committed after Elasticsearch accepts the write. Committing before the write risks losing catalog updates if the worker crashes between the offset commit and the Elasticsearch response. Accepting occasional replay is safer because deterministic product IDs make replay idempotent.

## Partial Updates From Multiple Sources

Future catalog ingestion will likely combine base product content, offer data, availability, price, seller state, and behavioral features. Those sources may update at different cadences. The current `source_versions` field gives each source a place to record its version, event ID, or timestamp.

Later partial-update handling should preserve source ownership: a price event should not overwrite title content, and a content event should not erase availability. Source-specific transforms plus scripted or document-merge updates can keep those boundaries explicit.

## ESCI Dataset Path

The Amazon ESCI dataset is useful for relevance experiments because it includes query-product judgments and product metadata. The first ingestion step should load unique product rows from `shopping_queries_dataset_products.parquet`, normalize them into this schema, and keep query judgments for evaluation rather than mixing them into product documents.