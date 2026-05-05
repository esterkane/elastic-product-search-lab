# Deployment-Safe Reindexing and ILM

This lab uses blue-green product-catalog indices so the searchable catalog can be rebuilt safely from canonical product snapshots. Product documents are written to a fresh concrete index, smoke checked, and then exposed by aliases in one atomic Elasticsearch alias update.

## Index Roles

| Name | Role | Lifecycle |
| --- | --- | --- |
| `products-v1`, `products-v2`, ... | Concrete product catalog builds | Kept on the content tier until manually retired |
| `products-read` | Stable API/evaluation read alias | Atomically moved after smoke checks |
| `products-write` | Canonical indexer write alias | Moved with `products-read` during deployment cutover |
| `product-events` | Event/audit data stream | ILM hot, warm, delete |
| `search-events` | Search telemetry/event data stream | ILM hot, warm, delete |

The product catalog is content data: it is user-facing, refreshed through controlled rebuilds, and usually needs predictable search latency. Event and telemetry streams are time-series data: they roll over and age out independently, so they can follow hot/warm/delete retention without coupling retention to catalog availability.

## Blue-Green Flow

1. Create a fresh concrete product index such as `products-v2`.
2. Load canonical JSONL snapshots or reindex from the current `products-read` alias.
3. Refresh the target index.
4. Run smoke checks for document count and required mapping fields.
5. Atomically switch `products-read` and `products-write` to the new concrete index.
6. Keep the previous concrete index available for rollback until the deployment is verified.

```powershell
.\scripts\reindex_and_switch.ps1 `
  --target-version 2 `
  --source-index products-read `
  --install-resources `
  --min-docs 1
```

To load a generated JSONL snapshot instead of using Elasticsearch `_reindex`:

```powershell
.\scripts\reindex_and_switch.ps1 `
  --target-version 2 `
  --input data\sample\products.jsonl `
  --install-resources `
  --min-docs 1
```

Use `--dry-run` to create, load, refresh, and smoke check the index without switching aliases.

## Rollback

The deployment script prints the previous concrete indices for both aliases. Roll back by switching both aliases back to the previous product index:

```powershell
.\scripts\reindex_and_switch.ps1 `
  --target-index products-v1 `
  --source-index products-v2 `
  --min-docs 1
```

For a read-only compatibility rollback, the older helper still works:

```powershell
.\.venv\Scripts\python.exe scripts\switch_product_alias.py --target-index products-v1
```

Prefer moving both `products-read` and `products-write` together when the canonical indexer is active.

## ILM Policies

Checked-in policy examples live under `config/ilm/`:

- `config/ilm/product-events-retention.json`: product source/audit events, 14 day retention.
- `config/ilm/search-events-retention.json`: search telemetry, 30 day retention.

The generated default in `src/search/index_management.py` installs `product-events-retention` with hot rollover, warm priority lowering, and delete retention. These policies are intentionally for event/audit data streams only. Product catalog indices do not use this time-based delete policy because a catalog version is retired only after replacement and rollback windows are understood.

Install generated resources:

```powershell
.\.venv\Scripts\python.exe scripts\create_index.py --install-resources --index products-v1
```

Install a checked-in ILM policy directly:

```powershell
curl -X PUT "http://localhost:9200/_ilm/policy/product-events-retention" `
  -H "Content-Type: application/json" `
  --data-binary "@config/ilm/product-events-retention.json"
```

## Smoke and Verification Commands

Check aliases:

```powershell
curl "http://localhost:9200/_alias/products-read?pretty"
curl "http://localhost:9200/_alias/products-write?pretty"
```

Check document count:

```powershell
curl "http://localhost:9200/products-read/_count?pretty"
```

Check shard size and placement:

```powershell
curl "http://localhost:9200/_cat/shards/products-v2?v&h=index,shard,prirep,state,store,node"
```

Check ILM state for event streams:

```powershell
curl "http://localhost:9200/product-events/_ilm/explain?pretty"
curl "http://localhost:9200/_data_stream/product-events?pretty"
```

## Operational Caveats

- Keep `PRODUCT_INDEX_REPLICAS=0` for single-node local development; use `1` or more only when the cluster has enough data nodes.
- Do not write partial product updates directly into `products-read`; rebuild canonical product documents and write through the controlled build/write path.
- Keep the previous concrete index until API smoke tests, relevance checks, and indexer health are verified.
- Product catalog tiering is a capacity decision. This lab defaults to content-tier-style behavior; event and telemetry streams are the only data with automatic warm/delete retention.
