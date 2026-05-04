# Read Path Strategy

## Purpose

The product search API reads from a stable canonical product index alias and optionally overlays a small set of volatile fields at response time. This keeps the main ranking path explainable while leaving room for live price and inventory freshness.

## Retrieval

Main candidate retrieval uses:

- `products-read` by default
- lexical BM25 across `title`, `brand`, `category`, `description`, and `catalog_text`
- optional mild boosts for `popularity_score` and `updated_at`

The query builder keeps the ranking path simple. Future ranking customizations should plug into the explicit extension point for:

- analytics ranking signals
- cohort or personalization tags
- merchandiser policies

Those extensions should remain additive and reviewable, not a hidden ingest-time merge.

## Volatile Overlay

The optional overlay is controlled by API environment variables:

```powershell
$env:PRODUCT_LIVE_OVERLAY_ENABLED="true"
$env:PRODUCT_LIVE_INDEX="products-live"
```

When enabled, `/search`:

1. Retrieves candidates from `products-read`.
2. Calls `mget` against `products-live` for returned product ids.
3. Merges only volatile fields into the response:
   - `price`
   - `currency`
   - `availability`

If the overlay is disabled or unavailable, the API returns canonical product fields from `products-read`.

## Suggest

Autocomplete/typeahead uses a separate index:

- default index: `product-suggest`
- API route: `GET /suggest?q=wire&size=5`
- builder: `scripts/build_product_suggest_index.py`

Build from canonical product snapshots:

```powershell
.\.venv\Scripts\python.exe scripts\build_product_suggest_index.py `
  --input data\sample\products.jsonl `
  --index product-suggest `
  --recreate
```

The suggest index uses a `search_as_you_type` field and does not require changes to `src/search/product_mapping.json`.

## Operational Boundary

The read path does not write to the product content index. Product document assembly remains upstream in the canonical builder and staged indexing flow. The overlay is intentionally small and response-scoped.
