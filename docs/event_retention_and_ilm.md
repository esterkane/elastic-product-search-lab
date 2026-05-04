# Event Retention And ILM

## Purpose

Product event and audit records are operational history, not the searchable product catalog. They should be stored separately from versioned product content indices and retained with a time-based lifecycle.

## Resources

The indexing resource installer creates:

| Resource | Default name | Purpose |
| --- | --- | --- |
| ILM policy | `product-events-retention` | Roll over event backing indices daily or at size threshold, then delete after the retention window. |
| Data stream template | `product-events-template` | Applies mappings and ILM settings to `product-events*` data streams. |
| Product template | `products-catalog-template` | Applies product search mapping/settings to `products-v*`. |
| Product pipeline | `products-minimal-normalization` | Last-mile product normalization only. |

## Data Stream Shape

The event/audit template maps common operational fields:

- `@timestamp`
- `event_time`
- `product_id`
- `source`
- `event_type`
- `trace_id`
- `correlation_id`
- `error_kind`
- `code`
- `payload`
- `metadata`
- `raw_event`
- `message`

`payload` and `metadata` are `flattened` so source-specific context can be stored without changing the product search mapping.

## Retention Defaults

The lab default retention is `14d`. This is a small local-development default, not a performance claim. Use the helper in `src/search/index_management.py` to generate a different policy:

```python
event_ilm_policy_body(retention_days=30)
```

## Operational Boundary

Use event/audit storage for replay traces, DLQ records, consumer errors, and indexing audit events. Use `products-v*` only for complete canonical product documents that are ready to serve search traffic.

Kafka/Redpanda topics remain the transport layer:

- `product.catalog`
- `product.price`
- `product.inventory`
- `product.reviews`
- `product.analytics`
- `product.dlq`

The Elasticsearch event/audit data stream is the retention layer for selected operational records from those flows.
