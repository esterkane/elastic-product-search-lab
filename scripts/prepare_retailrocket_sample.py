"""Prepare small deterministic RetailRocket product/event samples."""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.dataset_etl import (  # noqa: E402
    as_float,
    popularity_from_counts,
    read_records,
    stable_availability,
    stable_price,
    write_standard_outputs,
)

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "generated" / "retailrocket"


def latest_item_properties(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, tuple[int, Any]]] = defaultdict(dict)
    for row in records:
        item_id = str(row.get("itemid") or row.get("item_id") or "")
        prop = str(row.get("property") or "")
        if not item_id or not prop:
            continue
        timestamp = int(as_float(row.get("timestamp"), 0))
        current = grouped[item_id].get(prop)
        if current is None or timestamp >= current[0]:
            grouped[item_id][prop] = (timestamp, row.get("value"))
    return {item_id: {prop: value for prop, (_, value) in props.items()} for item_id, props in grouped.items()}


def prepare_retailrocket_sample(
    *,
    events: list[dict[str, Any]],
    item_properties: list[dict[str, Any]] | None = None,
    max_products: int = 100,
    seed: int = 17,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    properties = latest_item_properties(item_properties or [])
    product_counts: Counter[str] = Counter()
    event_type_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in events:
        product_id = str(row.get("itemid") or row.get("item_id") or "")
        event_type = str(row.get("event") or "").lower()
        if not product_id:
            continue
        weight = {"view": 1, "addtocart": 3, "transaction": 8}.get(event_type, 1)
        product_counts[product_id] += weight
        event_type_counts[product_id][event_type] += 1

    selected_ids = sorted(product_counts, key=lambda item_id: (-product_counts[item_id], item_id))[:max_products]
    products: list[dict[str, Any]] = []
    for product_id in selected_ids:
        props = properties.get(product_id, {})
        title = str(props.get("name") or props.get("title") or f"RetailRocket Item {product_id}")
        category = str(props.get("categoryid") or props.get("category") or "RetailRocket Imported Products")
        price = as_float(props.get("price"), stable_price(product_id, seed=seed))
        synthetic_price = "price" not in props
        products.append(
            {
                "product_id": f"RR-{product_id}",
                "title": title,
                "description": f"RetailRocket behavior-derived item {product_id}.",
                "brand": str(props.get("brand") or "retailrocket-unknown"),
                "category": category,
                "attributes": {
                    "source_dataset": "retailrocket",
                    "raw_item_id": product_id,
                    "view_count": event_type_counts[product_id]["view"],
                    "add_to_cart_count": event_type_counts[product_id]["addtocart"],
                    "transaction_count": event_type_counts[product_id]["transaction"],
                    "synthetic_catalog_title": "name" not in props and "title" not in props,
                    "synthetic_price": synthetic_price,
                    "synthetic_inventory": True,
                    "synthetic_reviews": True,
                },
                "price": price,
                "currency": "USD",
                "availability": stable_availability(product_id, seed=seed),
                "popularity_score": popularity_from_counts(product_counts, product_id),
                "seller_id": "retailrocket-dataset",
                "updated_at": "2026-01-01T00:00:00Z",
            }
        )
    return products, []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare RetailRocket product snapshots and canonical events.")
    parser.add_argument("--events", type=Path, required=True, help="RetailRocket events CSV or JSONL.")
    parser.add_argument("--item-properties", type=Path, default=None, help="Optional item_properties CSV or JSONL.")
    parser.add_argument("--max-products", type=int, default=100)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        products, judgments = prepare_retailrocket_sample(
            events=read_records(args.events),
            item_properties=read_records(args.item_properties) if args.item_properties else None,
            max_products=args.max_products,
            seed=args.seed,
        )
        outputs = write_standard_outputs(output_dir=args.output_dir, products=products, judgments=judgments, dataset="retailrocket")
        for name, path in outputs.items():
            print(f"Wrote {name} to {path}")
    except Exception as exc:  # noqa: BLE001 - CLI should print a clear local failure.
        print(f"RetailRocket sample preparation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
