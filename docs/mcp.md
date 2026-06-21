# Agent Access via MCP

A read-only [Model Context Protocol](https://modelcontextprotocol.io) server
exposes the product-search core as agent tools. It lets an MCP client
(Claude Code, Cursor, a LangGraph agent) run the lab's three comparable BM25
strategies and discover their names — without going through the HTTP API.

The server is **thin**: it contains no business logic. Each tool validates its
inputs and then calls the existing search functions in
[`src/search/strategies.py`](../src/search/strategies.py) — the same module the
evaluation and benchmark CLIs use. Both tools are **read-only**: they never
ingest, mutate the index, or write anything.

## Why Python

The three named, executable strategies (`baseline_bm25`, `boosted_bm25`,
`enriched_profile`) live in the Python search core. The TypeScript `apps/api`
service only has a baseline/boosted `boost` toggle and no `enriched_profile`
path, so the MCP server is implemented in Python with the official
[`mcp`](https://pypi.org/project/mcp/) SDK, wrapping the real strategy registry.

## Tools

### `product_search(query, strategy?, size?)`

Run one BM25 strategy against the product index and return shaped product hits.

| Input | Type | Default | Notes |
| --- | --- | --- | --- |
| `query` | string | — (required) | Non-empty natural-language query. |
| `strategy` | string | `enriched_profile` | One of `baseline_bm25`, `boosted_bm25`, `enriched_profile`. |
| `size` | int | `10` | 1–50 (matches the HTTP `/search` cap). |

Output (same shape as the HTTP `/search` response — normalized products, never
raw Elasticsearch hits):

```json
{
  "strategy": "boosted_bm25",
  "query": "running shoes",
  "took": 7,
  "total": 2,
  "count": 2,
  "products": [
    {
      "productId": "p1",
      "title": "Trail Running Shoe",
      "description": "...",
      "brand": "acme",
      "category": "footwear",
      "attributes": {},
      "price": 89.99,
      "currency": "USD",
      "availability": "in_stock",
      "popularityScore": 42.0,
      "sellerId": "seller-1",
      "updatedAt": "2026-01-01T00:00:00Z",
      "score": 12.3
    }
  ]
}
```

An empty `products` list with no error means nothing matched.

### `list_strategies()`

Return the executable strategy names with a one-line description each, plus the
default. No Elasticsearch call is made.

```json
{
  "count": 3,
  "default": "enriched_profile",
  "strategies": [
    { "name": "baseline_bm25", "description": "Plain multi-field BM25 ... The relevance baseline." },
    { "name": "boosted_bm25", "description": "BM25 plus a function_score that rewards popularity and recency ..." },
    { "name": "enriched_profile", "description": "BM25 over the deterministic ingestion-time search_profile field ..." }
  ]
}
```

## Error contract

Tools never raise or leak a stack trace. On failure they return a structured
payload instead of a result:

```json
{
  "isError": true,
  "errorCategory": "validation" | "transient" | "business",
  "isRetryable": false,
  "message": "<safe, human-readable summary>",
  "details": { }
}
```

| Category | When | Retryable |
| --- | --- | --- |
| `validation` | Empty `query`, unknown `strategy`, `size` out of range | no |
| `transient` | Elasticsearch unreachable / timed out | yes |
| `business` | A valid request that cannot be satisfied as asked | no |

Example — unknown strategy:

```json
{
  "isError": true,
  "errorCategory": "validation",
  "isRetryable": false,
  "message": "`strategy` must be one of ['baseline_bm25', 'boosted_bm25', 'enriched_profile'].",
  "details": { "strategy": "vector_only", "allowed": ["baseline_bm25", "boosted_bm25", "enriched_profile"] }
}
```

## Run it

The server needs the `mcp` extra installed and a reachable Elasticsearch with the
`products-v1` index loaded (see the repo README for `create_index` /
`load_sample_data`). `list_strategies` works without Elasticsearch;
`product_search` needs it.

```powershell
# Install the MCP extra into the local venv
.\.venv\Scripts\python.exe -m pip install -e ".[mcp]"

# Run the stdio server
npm run mcp
# equivalently:
.\.venv\Scripts\python.exe -m src.mcp.server
```

Configuration is read from the environment / `.env` exactly like the rest of the
lab: `ELASTICSEARCH_URL`, `ELASTICSEARCH_USE_AUTH`,
`ELASTICSEARCH_USERNAME`/`PASSWORD`, and `PRODUCT_INDEX` (default `products-v1`).

## Client registration

Register the stdio server with any MCP client. For Claude Code, add to your MCP
config (adjust the absolute paths):

```json
{
  "mcpServers": {
    "product-search-lab": {
      "command": "C:\\path\\to\\elastic-product-search-lab\\.venv\\Scripts\\python.exe",
      "args": ["-m", "src.mcp.server"],
      "cwd": "C:\\path\\to\\elastic-product-search-lab",
      "env": { "PRODUCT_INDEX": "products-v1" }
    }
  }
}
```

## Design notes / invariants

- **Thin + read-only.** No business logic in the MCP layer; tools validate and
  delegate to `src/search/strategies.py`. No writes, no ingestion.
- **Same shapes as the API.** `product_search` returns the normalized product
  objects the HTTP `/search` route returns, never raw ES hits.
- **Structured errors only.** Failures map to `validation` / `transient` /
  `business`; stack traces stay in the logs.
- **Comparability preserved.** The strategy registry is the single source of
  truth shared by the MCP tools, the evaluation CLI, and the benchmark CLI, so
  the three strategies stay side-by-side comparable and the search-quality gate
  is unaffected.
- **Lexical + enrichment is intentional.** The strategies are BM25-family;
  vector/hybrid retrieval remains an optional extra and is not exposed here.
```
