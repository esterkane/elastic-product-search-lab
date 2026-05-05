# Local Quickstarts

## JSONL Mode

JSONL mode is the default local path and does not require Kafka.

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
docker compose up -d elasticsearch kibana
.\scripts\check-es.ps1
.\.venv\Scripts\python.exe scripts\load_sample_data.py --switch-alias --install-resources
cd apps\api
npm install
npm run dev
```

Try:

```powershell
curl "http://localhost:3000/search?q=wireless%20mouse&debug=true"
```

## Kafka Mode

Kafka mode uses Redpanda and remains optional.

```powershell
docker compose -f docker-compose.yml `
  -f docker-compose.kafka.yml `
  up -d elasticsearch kibana redpanda redpanda-console

docker exec elastic-product-search-lab-redpanda rpk topic create -p 3 -r 1 product.catalog product.price product.inventory product.reviews product.analytics product.dlq

.\.venv\Scripts\python.exe -m pip install -e ".[kafka]"
.\.venv\Scripts\python.exe scripts\generate_synthetic_events.py --limit 5
.\.venv\Scripts\python.exe scripts\publish_events.py --input data\generated\synthetic_product_events.jsonl
```

See `docs/kafka_dev_flow.md` for topic details and DLQ behavior.

## Dataset Preparation

Raw files stay in ignored `data/raw/`. Small generated samples go to `data/generated/`.

```powershell
.\.venv\Scripts\python.exe scripts\prepare_esci_sample.py --products data\raw\shopping_queries_dataset_products.parquet --examples data\raw\shopping_queries_dataset_examples.parquet --standard-output-dir data\generated\esci
.\.venv\Scripts\python.exe scripts\prepare_retailrocket_sample.py --events data\raw\retailrocket\events.csv --item-properties data\raw\retailrocket\item_properties_part1.csv
.\.venv\Scripts\python.exe scripts\prepare_olist_sample.py --products data\raw\olist\olist_products_dataset.csv --order-items data\raw\olist\olist_order_items_dataset.csv --reviews data\raw\olist\olist_order_reviews_dataset.csv
```

See `docs/dataset_integration.md`.

## Reindex And Alias Cutover

```powershell
.\.venv\Scripts\python.exe scripts\load_sample_data.py --build-id 202605041300 --install-resources
.\.venv\Scripts\python.exe scripts\switch_product_alias.py --target-index products-v202605041300
```

One-command local rebuild:

```powershell
.\.venv\Scripts\python.exe scripts\load_sample_data.py --switch-alias --install-resources
```

## Shortcuts

Use `make` when available:

```bash
make dev-up
make dev-up-kafka
make load-sample
make build-canonical
make replay-events
make switch-alias INDEX=products-vlocal
```
