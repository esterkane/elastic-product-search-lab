# Migration Note

## Original Behavior Preserved

- Small checked-in JSONL product samples still load locally.
- `scripts/load_sample_data.py` still works without Kafka.
- `scripts/replay_product_events.py` still supports the original direct JSONL event replay.
- Existing relevance, benchmark, and quality-gate scripts remain available.
- The API `/search` route remains backward-compatible for normal search requests.

## New Baseline

- Complete product documents are assembled before indexing.
- New staged builds can write `products-v{build_id}` and cut over `products-read` atomically.
- The API defaults to `products-read`.
- CI runs Python tests plus API tests, build, and lint.

## Optional Layers

- Redpanda/Kafka-compatible event ingestion.
- Dataset adapters for ESCI, RetailRocket, and Olist.
- `product-suggest` autocomplete index and `/suggest` endpoint.
- `products-live` volatile read overlay.
- Policy/cohort governance layer via `SEARCH_POLICY_PATH`.

These optional layers can be adopted independently. The JSONL-only local demo remains the shortest path for contributors.
