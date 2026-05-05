# Canonical Ingestion

This lab indexes product search documents from canonical product state assembled in application code before Elasticsearch indexing. JSONL replay, Kafka consumers, and future batch jobs should call the same builder interface:

```python
from src.ingestion.canonical_builder import apply_source_update, build_canonical_product_document
from src.ingestion.source_state import ProductSourceState

state = ProductSourceState(product_id="P100001")
result = apply_source_update(state, source_update)
```

## Source Ownership

Each logical source owns a small field set. A source update that tries to write a non-owned field is rejected before it can change canonical state.

| Source | Owned fields |
| --- | --- |
| `catalog` | `title`, `description`, `brand`, `category`, `attributes`, `seller_id` |
| `seller` | `seller`, `seller_id`, `seller_name`, `seller_rating`, `is_marketplace` |
| `price` | `price`, `currency` |
| `inventory` | `availability` |
| `stock` | `stock`, `availability`, `stock_quantity`, `warehouse_id` |
| `reviews` | `average_rating`, `review_count` |
| `analytics` | `popularity_score` |
| `merchandising` | `merchandising`, `badges`, `boost_tags`, `campaign_ids`, `cohort_tags` |
| `lifecycle` | `lifecycle`, `is_deleted`, `deleted_at`, `delete_reason` |

## Precedence Rules

Merge precedence is explicit in `src/ingestion/source_state.py` as `SOURCE_PRECEDENCE`:

1. `catalog`
2. `seller`
3. `price`
4. `inventory`
5. `stock`
6. `analytics`
7. `reviews`
8. `merchandising`
9. `lifecycle`

Most fields are owned by only one source, so precedence usually does not matter. It is present for deliberate overlaps: `stock.availability` wins over legacy `inventory.availability`, and `lifecycle` wins for soft-delete fields.

## Source Versions And Guardrails

Every update carries `source_version`. For each source, the builder accepts only a newer version. Numeric clocks compare numerically; otherwise clocks compare as strings. A stale event is ignored and returns `False` from `ProductSourceState.apply()`, which makes out-of-order replay deterministic.

The emitted document stores:

- `source_versions`: latest accepted clock per source.
- `source_attribution`: field-to-source attribution such as `title: catalog@1` or `price: price@2`.
- `schema_version`: current canonical document schema version, currently `catalog-v2`.

## Tombstones And Soft Deletes

Lifecycle updates are the only source that may soft-delete a product. A tombstone is represented with:

```json
{
  "source": "lifecycle",
  "product_id": "P100001",
  "source_version": 5,
  "fields": {
    "is_deleted": true,
    "deleted_at": "2026-05-01T16:00:00Z",
    "delete_reason": "source_tombstone"
  }
}
```

If a product has enough catalog, price, seller, and stock state, the builder emits a full document with `is_deleted: true`. If the tombstone arrives before the rest of the product, the builder emits a minimal non-searchable tombstone document keyed by the same deterministic product ID. Search routes should filter `is_deleted:false` for customer-facing retrieval; event and audit retention remains separate.

## Deterministic IDs And Timestamps

The deterministic Elasticsearch document ID is the canonical `product_id`. The builder does not derive IDs from mutable title, seller, price, or event offsets.

Timestamp rules:

- `updated_at` is the max accepted source `updated_at`.
- `indexed_at` is supplied by the caller during deterministic rebuilds, or set at build time for ad hoc indexing.
- The ingest pipeline sets `indexed_at` only if it is missing.

## Source Hygiene

The builder keeps `_source` reviewable:

- known transient keys such as `raw_event`, `debug`, `_debug`, and `_tmp` are removed;
- attribute bags are sorted and kept under `attributes` as `flattened`;
- derived text fields (`catalog_text`, `autosuggest`, `search_profile`) are rebuilt from canonical state;
- evaluation labels are not copied into searchable product documents.

The Elasticsearch mapping is `dynamic: strict`, so unexpected top-level fields fail fast instead of silently polluting the index.

## Ingest Pipeline

The optional pipeline in `config/products-minimal-normalization.pipeline.json` is intentionally last-mile only:

- uppercases `currency`, `price_info.currency`, and offer currencies;
- lowercases `availability` and `stock.availability`;
- sets `indexed_at` when missing;
- sets `schema_version` when missing;
- removes known transient top-level fields.

It must not perform source merging, last-write-wins checks, tombstone interpretation, or business precedence. Those decisions stay in Python so JSONL replay and Kafka consumption produce the same output.

Install the pipeline:

```bash
curl -X PUT "http://localhost:9200/_ingest/pipeline/products-minimal-normalization" \
  -H "Content-Type: application/json" \
  --data-binary @config/products-minimal-normalization.pipeline.json
```

Validate with `_simulate`:

```bash
curl -X POST "http://localhost:9200/_ingest/pipeline/products-minimal-normalization/_simulate" \
  -H "Content-Type: application/json" \
  -d '{
    "docs": [
      {
        "_source": {
          "product_id": "P100001",
          "schema_version": "catalog-v2",
          "currency": "eur",
          "availability": "IN_STOCK",
          "price_info": {"currency": "eur"},
          "offers": [{"currency": "eur"}],
          "raw_event": {"trace": "remove-me"}
        }
      }
    ]
  }'
```

## Good Vs Bad Decisions

Good:

- Assemble one canonical document before indexing.
- Keep source ownership explicit and reject non-owned fields.
- Preserve source clocks and field attribution in the indexed document.
- Rebuild a versioned staging index and switch aliases atomically.
- Keep event/audit data in a separate stream with its own retention.

Bad:

- Let every producer issue direct partial updates into the customer-facing search index.
- Depend on Elasticsearch ingest pipelines for cross-source business merges.
- Treat Kafka offset order as the only conflict-resolution rule.
- Let price events overwrite title, category, or merchandising fields.
- Copy evaluation judgments or raw source events into `_source`.

Direct ad hoc upserts are fragile because they make index state depend on arrival order, retry behavior, and whichever producer wrote last. The canonical builder makes state reconstruction testable: given the same accepted source versions, rebuilds produce the same document.
