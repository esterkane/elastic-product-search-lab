# Optional Kafka Dev Flow

## Purpose

Kafka-compatible ingestion is optional. The lab still works as a file-driven Elasticsearch product-search demo with `scripts/load_sample_data.py` and the existing `scripts/replay_product_events.py` direct JSONL replay path.

Use the Kafka path when you want to test production-shaped event flow: per-source topics, source clocks, retryable vs non-retryable errors, DLQ behavior, and canonical product assembly before indexing.

## Local Services

Start Elasticsearch, Kibana, Redpanda, and Redpanda Console:

```powershell
docker compose -f docker-compose.yml `
  -f docker-compose.kafka.yml `
  up -d elasticsearch kibana redpanda redpanda-console
```

Check Elasticsearch and Kibana:

```powershell
.\scripts\check-es.ps1
.\scripts\check-kibana.ps1
```

Open:

- Elasticsearch: `http://localhost:9200`
- Kibana: `http://localhost:5601`
- Redpanda Console: `http://localhost:8080`
- Kafka bootstrap from host: `localhost:19092`

## Topics

Topic definitions live in `config/kafka-topics.json`. The indexing-specific contracts, replay semantics, and rollback flow are detailed in `docs/kafka_indexing.md`.

| Topic | Source | Purpose |
| --- | --- | --- |
| `product.catalog` | `catalog` | Title, description, brand, category, attributes, seller identity |
| `product.price` | `price` | Price and currency |
| `product.inventory` | `inventory` | Availability |
| `product.reviews` | `reviews` | Future review aggregates |
| `product.analytics` | `analytics` | Popularity and behavioral features |
| `product-change` | `catalog`, `seller` | Product/seller changes for the indexer contract |
| `price-stock` | `price`, `inventory`, `stock` | Price, inventory, and stock changes for the indexer contract |
| `merchandising` | `merchandising`, `analytics` | Merchandising and analytics signals |
| `delete` | `lifecycle` | Tombstones and soft deletes |
| `product.dlq` | dead letter | Malformed or non-retryable events |

Create topics with Redpanda CLI:

```powershell
docker exec elastic-product-search-lab-redpanda rpk topic create -p 3 -r 1 product.catalog product.price product.inventory product.reviews product.analytics product-change price-stock merchandising delete product.dlq
```

## Event Schema

Kafka events use `src/ingestion/event_schema.py`:

```json
{
  "source": "catalog",
  "event_type": "snapshot",
  "product_id": "P100001",
  "source_version": "2026-05-01T10:00:00Z",
  "event_time": "2026-05-01T10:00:00Z",
  "payload": {
    "title": "Example product",
    "description": "Source-owned catalog fields only",
    "brand": "Example",
    "category": "Demo",
    "attributes": {},
    "seller_id": "seller-1"
  },
  "trace_id": "trace-00001-catalog",
  "correlation_id": "synthetic-P100001"
}
```

Validation rules:

- `source` must be one of `catalog`, `price`, `inventory`, `reviews`, or `analytics`.
- `payload` may only contain fields owned by that source.
- `event_time` must include a timezone.
- `snapshot` and `upsert` events require a non-empty payload.

## Generate And Publish Events

Install optional Kafka dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[kafka]"
```

Generate canonical source events from the sample catalog:

```powershell
.\.venv\Scripts\python.exe scripts\generate_synthetic_events.py --limit 5
```

Publish generated events:

```powershell
.\.venv\Scripts\python.exe scripts\publish_events.py `
  --input data\generated\synthetic_product_events.jsonl `
  --bootstrap-servers localhost:19092
```

## Consume Events

`src/ingestion/kafka_consumer.py` contains the broker-agnostic consumer core:

- `process_raw_event(...)` parses and validates raw event bytes.
- `process_event(...)` applies source updates to `ProductSourceState`.
- Complete canonical documents are indexed through an `IndexSink`.
- Malformed or non-retryable events are routed through a `DlqSink`.
- Retryable downstream failures are returned as `failed_retryable` so the caller can avoid committing offsets.

The low-level `consume_forever(...)` function expects a configured `confluent_kafka.Consumer`, an index sink, a state store, and a DLQ sink. A production worker should replace the in-memory state store with durable per-product state.

Run the lab indexer:

```powershell
.\.venv\Scripts\python.exe scripts\run_kafka_indexer.py --index products-build
```

## JSONL Replay Compatibility

The original direct partial-update replay still works:

```powershell
.\.venv\Scripts\python.exe scripts\replay_product_events.py
```

Canonical JSONL events can also be replayed through the canonical builder:

```powershell
.\.venv\Scripts\python.exe scripts\generate_synthetic_events.py --limit 5
.\.venv\Scripts\python.exe scripts\replay_product_events.py `
  --canonical-events data\generated\synthetic_product_events.jsonl
```

## Error Handling

Retryable:

- Incomplete canonical products because not all source-owned data has arrived.
- Temporary index sink or broker failures.

Non-retryable:

- Malformed JSON.
- Schema validation failures.
- Payload fields not owned by the declared source.

Non-retryable events go to `product.dlq` with structured context: `code`, `message`, `error_kind`, `product_id`, raw event, and broker metadata.
