PYTHON ?= python
COMPOSE ?= docker compose
PROJECT ?= elastic-product-search-lab
BUILD_ID ?= local
INDEX ?= products-vlocal

.PHONY: dev-up dev-up-kafka dev-down load-sample replay-events build-canonical run-kafka-indexer switch-alias build-suggest test-python test-api lint-api

dev-up:
	$(COMPOSE) -p $(PROJECT) up -d elasticsearch kibana

dev-up-kafka:
	$(COMPOSE) -p $(PROJECT) -f docker-compose.yml -f docker-compose.kafka.yml up -d elasticsearch kibana redpanda redpanda-console redpanda-topic-init

dev-down:
	$(COMPOSE) -p $(PROJECT) -f docker-compose.yml -f docker-compose.kafka.yml down

load-sample:
	$(PYTHON) scripts/load_sample_data.py

replay-events:
	$(PYTHON) scripts/replay_product_events.py

build-canonical:
	$(PYTHON) scripts/generate_synthetic_events.py --input data/sample/products.jsonl --output data/generated/synthetic_product_events.jsonl

run-kafka-indexer:
	$(PYTHON) scripts/run_kafka_indexer.py --index $(INDEX)

switch-alias:
	$(PYTHON) scripts/switch_product_alias.py --target-index $(INDEX)

build-suggest:
	$(PYTHON) scripts/build_product_suggest_index.py --input data/sample/products.jsonl --index product-suggest --recreate

test-python:
	$(PYTHON) -m pytest tests/python -m "not integration"

test-api:
	cd apps/api && npm test

lint-api:
	cd apps/api && npm run lint && npm run build
