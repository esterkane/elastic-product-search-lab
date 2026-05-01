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

## Simulated Catalog Change Events

The event replay path shows how one upstream change becomes one deterministic Elasticsearch document update. Each event carries an `event_id`, `product_id`, `source_system`, `event_type`, `event_time`, `payload`, and numeric `source_version`. The consumer always targets `_id = product_id`, so a title, price, availability, category, seller, attribute, or delete/unavailable event updates the same document that bulk ingestion created.

`updated_at` comes from the business event time because search freshness should reflect when the catalog state changed. `indexed_at` comes from the ingestion worker time because operators need to measure pipeline lag separately from business time.

## Index, Update, Upsert, and Scripted Updates

A full product snapshot should use an index operation because the incoming record owns the complete searchable document. A partial catalog event should use an update operation because it only owns a few fields. `doc_as_upsert` is intentionally not used for the current simulated events: a price-only or availability-only event cannot safely create a complete searchable product. It would produce documents missing title, category, description, and other relevance fields.

`doc_as_upsert` becomes appropriate only when the event payload is a complete product snapshot or when the consumer can hydrate missing fields from a trusted product store before writing. Scripted updates are useful when Elasticsearch must merge nested state atomically, increment counters, or guard on values inside the document. This lab performs the merge in Python for readability: it reads `source_versions`, checks freshness, then writes a merged partial document with `retry_on_conflict` enabled.

## Multi-Source Updates Into One Document

Product search documents are assembled from multiple source systems. Content owns title and description, taxonomy owns category, inventory owns availability, pricing owns price and currency, seller systems own seller enrichment, and behavioral systems may own popularity features. The `source_versions` map records the latest accepted version per source system so one source can update its fields without erasing another source's progress.

## Idempotency and Replay Safety

Replaying accepted events should converge on the same product document instead of creating duplicates or rolling fields backward. Deterministic document IDs handle the duplicate-document problem. Source-specific version checks handle the stale-update problem. If an event arrives with a `source_version` that is equal to or older than the latest accepted version for that `source_system`, the consumer skips it and logs `product_event_skipped_stale`.

This behavior also supports safer queue processing. Kafka offsets should only be committed after Elasticsearch accepts the write or the event is explicitly classified as stale. If the worker crashes before committing, replaying the event is acceptable because deterministic IDs and source versions make the write idempotent.

## Stale Event Protection

Distributed catalog systems can deliver events out of order. For example, inventory version 88 may mark a product as `limited_stock`, and version 80 may arrive later from a delayed partition. Without stale protection, the older event could incorrectly restore `in_stock`. The consumer compares the event's `source_version` against `source_versions[source_system]` and skips older or equal versions.

The local sample file includes this case so the replay command demonstrates both accepted updates and a skipped stale event.
