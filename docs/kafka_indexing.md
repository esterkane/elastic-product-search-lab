# Kafka Indexing Path

## Purpose

The optional Kafka indexing path consumes source-owned product events, rebuilds canonical product documents in application code, and writes complete documents to Elasticsearch. The file-driven JSONL lab still works without Kafka.

Runtime choice: the indexer is Python because the canonical builder, source-state model, and existing bulk/index scripts are already Python. This avoids duplicating merge logic in a second runtime.

## Local Startup

```powershell
docker compose -f docker-compose.yml `
  -f docker-compose.kafka.yml `
  up -d elasticsearch kibana redpanda redpanda-console redpanda-topic-init
```

Install optional Kafka support:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[kafka]"
```

Run the indexer:

```powershell
.\.venv\Scripts\python.exe scripts\run_kafka_indexer.py `
  --index products-build `
  --bootstrap-servers localhost:19092
```

## Topic Contracts

The lab supports both source-specific topics and higher-level indexer aliases. Events still include a `source` field, so the topic is a routing contract rather than the ownership source of truth.

| Topic | Accepted sources | Purpose |
| --- | --- | --- |
| `product.catalog` | `catalog`, `lifecycle` | Backward-compatible catalog and delete events |
| `product.price` | `price` | Backward-compatible price events |
| `product.inventory` | `inventory`, `stock` | Backward-compatible availability/stock events |
| `product.reviews` | `reviews` | Review aggregate events |
| `product.analytics` | `analytics`, `merchandising` | Analytics and merchandising events |
| `product-change` | `catalog`, `seller` | Product and seller changes |
| `price-stock` | `price`, `inventory`, `stock` | Price, inventory, and stock changes |
| `merchandising` | `merchandising`, `analytics` | Merchandising controls and ranking signals |
| `delete` | `lifecycle` | Tombstones and soft deletes |
| `product.dlq` | dead letter | Malformed or non-retryable records |

Topic definitions live in `config/kafka-topics.json`, and `docker-compose.kafka.yml` includes `redpanda-topic-init` for local creation.

## Event Contract

Each message value is a JSON `ProductSourceEvent`:

```json
{
  "source": "price",
  "event_type": "upsert",
  "product_id": "P100001",
  "source_version": 2,
  "event_time": "2026-05-01T10:00:00Z",
  "payload": {
    "price": 54.99,
    "currency": "eur"
  },
  "trace_id": "trace-price-2",
  "correlation_id": "corr-P100001"
}
```

Source ownership is enforced before state changes. A price event cannot write title, brand, category, merchandising, or delete fields.

## Replay And Idempotency

Replay is safe because:

- source versions are last-write-wins per source;
- stale source versions are skipped;
- repeated broker deliveries are deduplicated by `topic:partition:offset` when metadata is available;
- Elasticsearch writes use deterministic `_id = product_id`;
- the write operation is a bulk `index`, so the same canonical document converges on one Elasticsearch document.

Canonical JSONL replay uses the same `ProductEventIndexer`:

```powershell
.\.venv\Scripts\python.exe scripts\generate_synthetic_events.py --limit 5
.\.venv\Scripts\python.exe scripts\replay_product_events.py `
  --canonical-events data\generated\synthetic_product_events.jsonl `
  --index products-build
```

## Retry And Dead Letter Strategy

Retryable:

- incomplete canonical products, because the missing source may arrive later;
- Elasticsearch `429`, `502`, `503`, `504`;
- transient transport failures.

Non-retryable:

- malformed JSON;
- schema validation failures;
- source ownership violations;
- Elasticsearch mapping errors;
- Elasticsearch `409` version conflicts.

`429` and transient failures use exponential backoff with jitter:

```text
delay = initial_backoff_seconds * 2^attempt + jitter
```

After retries are exhausted, retryable indexing failures return `failed_retryable`, and the Kafka loop does not commit that offset. Non-retryable records are published to `product.dlq` with `code`, `message`, `error_kind`, `product_id`, `raw_event`, and broker metadata.

## 409 And 429 Handling

- `429`: retry with exponential backoff because Elasticsearch is applying backpressure.
- `409`: classify as non-retryable conflict. The current sink uses idempotent `index` writes, so `409` is not expected in normal operation. If a future sink adds optimistic concurrency controls, conflicts should be investigated or sent to DLQ instead of retried forever.

The primary consistency mechanism remains the canonical builder and per-source clocks, not Elasticsearch conflict retries.

## Observability Counters

`IndexerCounters` tracks:

- `processed`
- `indexed`
- `incomplete`
- `stale`
- `duplicate`
- `dlq`
- `retryable_failed`
- `non_retryable_failed`
- `retries`
- `conflicts`

The code logs structured JSON events such as `indexer_bulk_retry`, `canonical_product_indexed`, `product_event_duplicate_skipped`, and `product_event_sent_to_dlq`.

Consumer lag should be monitored from Kafka/Redpanda consumer group metrics. For local Redpanda:

```powershell
docker exec elastic-product-search-lab-redpanda `
  rpk group describe product-catalog-indexer --brokers=localhost:9092
```

## Rollback Procedure

The Kafka indexer should write to a staging/build index such as `products-build` or a versioned `products-v{build_id}` index.

1. Stop the indexer.
2. Leave `products-read` pointed at the last known-good product index.
3. Inspect DLQ and indexing counters.
4. Fix source data, schema, or mapping problems.
5. Replay from the earliest needed offset or JSONL event fixture.
6. Validate the rebuilt index.
7. Switch `products-read` only after validation passes.

If a bad index was already cut over, switch `products-read` back to the previous concrete index with `scripts/switch_product_alias.py`.
