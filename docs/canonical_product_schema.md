# Canonical Product Schema

## Purpose

The product catalog index is production-shaped while still small enough for this lab. Elasticsearch receives one canonical product document per product, assembled before indexing from source-owned state:

- catalog facts
- seller facts
- stock and availability
- price
- merchandising controls
- soft-delete lifecycle state

Business merging stays in the canonical builder, not in Elasticsearch ingest pipelines.

## Index And Aliases

Use versioned concrete product indices and aliases:

- write/build target: `products-v{build_id}`
- read alias: `products-read`
- optional build alias: `products-build`

Create and cut over:

```powershell
.\.venv\Scripts\python.exe scripts\load_sample_data.py --build-id 202605051200 --install-resources
.\.venv\Scripts\python.exe scripts\switch_product_alias.py --target-index products-v202605051200
```

## Mapping Choices

| Field | Mapping | Why |
| --- | --- | --- |
| `title` | `text` with `keyword` and `search_as_you_type` multi-field | Full-text ranking, exact aggregations, and typeahead support |
| `autosuggest` | `search_as_you_type` | Dedicated suggest text without changing ranking fields |
| `brand`, `category`, `seller_id`, `cohort_tags` | `keyword` | Facets, filters, policies, and cohort boosts |
| `attributes` | `flattened` | Unpredictable product attribute bags |
| `offers` | `nested` | Preserve price/seller/availability relationships per offer |
| `seller`, `stock`, `price_info`, `merchandising`, `lifecycle` | structured objects | Explainable source-domain sections |
| `embedding`, `semantic_embedding` | `dense_vector` | Configurable semantic retrieval experiments |
| `is_deleted`, `deleted_at` | boolean/date | Soft-delete state kept in the canonical document |
| `schema_version`, `source_versions`, `source_attribution` | keyword/flattened | Reviewable schema and provenance metadata |

The mapping remains `dynamic: strict` so accidental fields fail loudly.

## Canonical Document Shape

Top-level compatibility fields remain:

- `price`
- `currency`
- `availability`
- `seller_id`
- `popularity_score`

Production-shaped sections are emitted alongside them:

```json
{
  "schema_version": "catalog-v2",
  "product_id": "P100001",
  "title": "Organic coffee beans",
  "seller": {
    "seller_id": "kaufland",
    "seller_name": "Kaufland",
    "seller_rating": 4.8,
    "is_marketplace": false
  },
  "stock": {
    "availability": "limited_stock",
    "stock_quantity": 7,
    "warehouse_id": "berlin-1"
  },
  "price_info": {
    "amount": 8.99,
    "currency": "EUR"
  },
  "offers": [
    {
      "offer_id": "P100001:kaufland",
      "seller_id": "kaufland",
      "price": 8.99,
      "currency": "EUR",
      "availability": "limited_stock",
      "stock_quantity": 7,
      "is_buy_box": true
    }
  ],
  "merchandising": {
    "badges": ["bio"],
    "boost_tags": ["coffee-week"],
    "campaign_ids": ["spring"]
  },
  "lifecycle": {
    "is_deleted": false,
    "deleted_at": null,
    "delete_reason": ""
  },
  "source_versions": {
    "catalog": "1",
    "price": "2",
    "stock": "1"
  },
  "source_attribution": {
    "title": "catalog@1",
    "price": "price@2",
    "stock": "stock@1"
  }
}
```

## Semantic Mode

The checked-in mapping includes `dense_vector` fields with 384 dimensions for local vector experiments. Treat semantic retrieval as optional: lexical BM25 and boosted relevance remain the baseline.

## Curl Validation

Validate aliases:

```bash
curl -u elastic:$ELASTIC_PASSWORD "http://localhost:9200/_alias/products-read?pretty"
```

Inspect mapping choices:

```bash
curl -u elastic:$ELASTIC_PASSWORD "http://localhost:9200/products-read/_mapping?pretty"
```

Check nested offer querying:

```bash
curl -u elastic:$ELASTIC_PASSWORD -H "Content-Type: application/json" \
  "http://localhost:9200/products-read/_search?pretty" \
  -d '{"query":{"nested":{"path":"offers","query":{"bool":{"filter":[{"term":{"offers.seller_id":"kaufland"}},{"range":{"offers.price":{"lte":20}}}]}}}}}'
```

Validate autosuggest field:

```bash
curl -u elastic:$ELASTIC_PASSWORD -H "Content-Type: application/json" \
  "http://localhost:9200/products-read/_search?pretty" \
  -d '{"query":{"multi_match":{"query":"wire","type":"bool_prefix","fields":["autosuggest","autosuggest._2gram","autosuggest._3gram"]}}}'
```

Filter out soft-deleted documents:

```bash
curl -u elastic:$ELASTIC_PASSWORD -H "Content-Type: application/json" \
  "http://localhost:9200/products-read/_search?pretty" \
  -d '{"query":{"bool":{"filter":[{"term":{"is_deleted":false}}]}}}'
```
