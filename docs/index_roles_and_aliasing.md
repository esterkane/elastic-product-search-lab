# Index Roles And Aliasing

## Purpose

The searchable product catalog is built from complete canonical product documents. Rebuilds should target a fresh concrete index first, validate that index, and then atomically switch a read alias. This keeps the main search surface away from many direct partial writers.

## Product Index Roles

| Name | Role | Owner |
| --- | --- | --- |
| `products-v{build_id}` | Concrete versioned product index built from canonical snapshots. | Batch/rebuild job |
| `products-build` | Optional alias for the currently loading staging index. | Batch/rebuild job |
| `products-read` | Stable read alias for API, evaluation, and benchmark workflows. | Alias switch step |

`products-v1` remains available for the original local demo path. New rebuilds should prefer `products-vYYYYMMDDHHMM` or another deterministic build id.

## Rebuild Flow

1. Install index resources:

   ```powershell
   .\.venv\Scripts\python.exe scripts\create_index.py --install-resources
   ```

2. Build a staged product index from sample product snapshots:

   ```powershell
   .\.venv\Scripts\python.exe scripts\load_sample_data.py `
     --build-id 202605041245 `
     --install-resources
   ```

3. Validate the staged index with counts, sample queries, relevance checks, or manual inspection.

4. Switch the read alias:

   ```powershell
   .\.venv\Scripts\python.exe scripts\switch_product_alias.py `
     --target-index products-v202605041245
   ```

A one-command lab rebuild can load and switch after the basic count validation:

```powershell
.\.venv\Scripts\python.exe scripts\load_sample_data.py --switch-alias --install-resources
```

## Settings

Lab defaults are intentionally small:

- `PRODUCT_INDEX_SHARDS=1`
- `PRODUCT_INDEX_REPLICAS=0`

Use `--shards` and `--replicas` on `scripts/create_index.py` or `scripts/load_sample_data.py` to override. For a multi-node cluster, use at least one replica, for example `--replicas 1`.

The product index template applies to `products-v*` and contains the existing strict product mapping from `src/search/product_mapping.json`.

## Ingest Pipeline Scope

The product pipeline is intentionally last-mile only:

- uppercase `currency`
- lowercase `availability`
- set `indexed_at` when missing

It must not merge catalog, price, inventory, review, or analytics business fields. Source ownership and canonical assembly stay in `src/ingestion/source_state.py` and `src/ingestion/canonical_builder.py`.

## Pointing Evaluation At The Alias

Evaluation and benchmark scripts can use the read alias wherever they accept an index name:

```powershell
$env:PRODUCT_INDEX="products-read"
npm run evaluate:relevance
```

The alias switch is atomic from the Elasticsearch point of view: readers using `products-read` see either the previous concrete index or the new one.
