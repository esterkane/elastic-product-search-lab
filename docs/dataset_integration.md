# Dataset Integration

## Purpose

The lab supports small deterministic samples from public commerce datasets so local workflows can exercise catalog ingestion, source-owned event generation, review enrichment, analytics ranking signals, and offline evaluation.

Generated files stay small and are written as JSONL:

| Output | Shape | Consumer |
| --- | --- | --- |
| `product_snapshots.jsonl` | Complete Product-shaped snapshots | `scripts/load_sample_data.py` |
| `price_events.jsonl` | `ProductSourceEvent` with `source=price` | Canonical JSONL replay or Kafka producer |
| `inventory_events.jsonl` | `ProductSourceEvent` with `source=inventory` | Canonical JSONL replay or Kafka producer |
| `review_events.jsonl` | `ProductSourceEvent` with `source=reviews` | Canonical source state / future review enrichment |
| `analytics_events.jsonl` | `ProductSourceEvent` with `source=analytics` | Canonical source state / ranking features |
| `judgments.jsonl` | Query/product relevance labels | Offline evaluation |

Evaluation labels must remain in `judgments.jsonl`. They are never copied into searchable product documents.

A tiny checked-in example output set lives under `data/sample/dataset_demo/` for schema review without downloading raw datasets.

## Amazon ESCI

Source fields:

- Products: `product_id`, `product_title`, `product_description`, `product_bullet_point`, `product_brand`, `product_color`, `product_locale`
- Examples: `query`, `product_id`, `esci_label`

Lab use:

- Catalog ingestion from product metadata.
- Offline evaluation from ESCI labels mapped to grades: exact `3`, substitute `2`, complement `1`, irrelevant `0`.
- Synthetic price and inventory because ESCI does not provide live commerce state.

Command:

```powershell
.\.venv\Scripts\python.exe scripts\prepare_esci_sample.py `
  --products data\raw\shopping_queries_dataset_products.parquet `
  --examples data\raw\shopping_queries_dataset_examples.parquet `
  --max-queries 100 `
  --max-products 1000 `
  --standard-output-dir data\generated\esci
```

Licensing/citation: follow the Amazon ESCI dataset license and citation guidance from its source distribution. Keep raw files under ignored `data/raw/`.

## RetailRocket

Source fields:

- Events: `timestamp`, `visitorid`, `event`, `itemid`, optional `transactionid`
- Item properties: `timestamp`, `itemid`, `property`, `value`

Lab use:

- Analytics ranking signals from behavior counts. Transactions are weighted higher than add-to-cart events, which are weighted higher than views.
- Catalog snapshots from latest item properties where available.
- Synthetic product title, price, inventory, and reviews where RetailRocket does not provide stable fields.

Command:

```powershell
.\.venv\Scripts\python.exe scripts\prepare_retailrocket_sample.py `
  --events data\raw\retailrocket\events.csv `
  --item-properties data\raw\retailrocket\item_properties_part1.csv `
  --max-products 100 `
  --output-dir data\generated\retailrocket
```

Licensing/citation: follow the RetailRocket dataset terms from its distribution page. This repo does not vendor the raw dataset.

## Olist

Source fields:

- Products: `product_id`, `product_category_name`, dimensions, photo count, text length fields
- Order items: `order_id`, `product_id`, `seller_id`, `price`
- Reviews: `order_id`, `review_score`

Lab use:

- Catalog snapshots from product category and physical attributes.
- Price from order item prices.
- Review enrichment from order review scores.
- Analytics popularity from sales counts.
- Synthetic inventory because Olist does not provide current stock state.

Command:

```powershell
.\.venv\Scripts\python.exe scripts\prepare_olist_sample.py `
  --products data\raw\olist\olist_products_dataset.csv `
  --order-items data\raw\olist\olist_order_items_dataset.csv `
  --reviews data\raw\olist\olist_order_reviews_dataset.csv `
  --max-products 100 `
  --output-dir data\generated\olist
```

Licensing/citation: follow Olist Brazilian E-Commerce dataset terms from its source distribution. Keep raw files outside Git.

## WDC Product Corpus

WDC product corpus or product matching support is not implemented in this phase. It is a good next adapter for entity resolution and duplicate-product matching experiments, but its schema variants need a separate small mapping contract.

## Synthetic Fields

Synthetic values are deterministic with a fixed seed. Product snapshots mark synthetic augmentations in `attributes`, for example:

- `synthetic_price`
- `synthetic_inventory`
- `synthetic_reviews`
- `synthetic_catalog_title`

These markers separate source facts from lab-friendly generated fields.

## Feeding Replay Or Kafka

Each source event file contains valid `ProductSourceEvent` rows. To publish one stream:

```powershell
.\.venv\Scripts\python.exe scripts\publish_events.py --input data\generated\olist\analytics_events.jsonl
```

To replay a complete canonical event set through the JSONL path, first convert product snapshots into catalog, price, inventory, and analytics events:

```powershell
.\.venv\Scripts\python.exe scripts\generate_synthetic_events.py `
  --input data\generated\olist\product_snapshots.jsonl `
  --output data\generated\olist\canonical_events.jsonl

.\.venv\Scripts\python.exe scripts\replay_product_events.py `
  --canonical-events data\generated\olist\canonical_events.jsonl
```

The dataset-specific `review_events.jsonl` file can be published to Kafka or stored as event/audit data. Current searchable product documents do not mix review labels or evaluation judgments into the content index.
