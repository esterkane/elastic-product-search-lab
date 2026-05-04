"""Generate canonical source-owned product events for Kafka or JSONL replay."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.load_sample_data import load_products  # noqa: E402
from src.ingestion.event_schema import ProductSourceEvent  # noqa: E402

DEFAULT_INPUT = PROJECT_ROOT / "data" / "sample" / "products.jsonl"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "generated" / "synthetic_product_events.jsonl"


def product_events(product, sequence: int) -> list[ProductSourceEvent]:
    version = product.updated_at.isoformat().replace("+00:00", "Z")
    event_time = product.updated_at.astimezone(timezone.utc)
    correlation_id = f"synthetic-{product.product_id}"
    return [
        ProductSourceEvent(
            source="catalog",
            event_type="snapshot",
            product_id=product.product_id,
            source_version=version,
            event_time=event_time,
            payload={
                "title": product.title,
                "description": product.description,
                "brand": product.brand,
                "category": product.category,
                "attributes": product.attributes,
                "seller_id": product.seller_id,
            },
            trace_id=f"trace-{sequence:05d}-catalog",
            correlation_id=correlation_id,
        ),
        ProductSourceEvent(
            source="price",
            event_type="snapshot",
            product_id=product.product_id,
            source_version=version,
            event_time=event_time,
            payload={"price": product.price, "currency": product.currency},
            trace_id=f"trace-{sequence:05d}-price",
            correlation_id=correlation_id,
        ),
        ProductSourceEvent(
            source="inventory",
            event_type="snapshot",
            product_id=product.product_id,
            source_version=version,
            event_time=event_time,
            payload={"availability": product.availability},
            trace_id=f"trace-{sequence:05d}-inventory",
            correlation_id=correlation_id,
        ),
        ProductSourceEvent(
            source="analytics",
            event_type="snapshot",
            product_id=product.product_id,
            source_version=version,
            event_time=event_time,
            payload={"popularity_score": product.popularity_score},
            trace_id=f"trace-{sequence:05d}-analytics",
            correlation_id=correlation_id,
        ),
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate canonical product source events.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Input complete product JSONL file.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output canonical event JSONL file.")
    parser.add_argument("--limit", type=int, default=None, help="Optional product limit for small demos.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    products = load_products(args.input)
    if args.limit is not None:
        products = products[: args.limit]
    args.output.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with args.output.open("w", encoding="utf-8") as output:
        for sequence, product in enumerate(products, start=1):
            for event in product_events(product, sequence):
                output.write(event.to_json_line() + "\n")
                count += 1

    print(f"wrote_events={count}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

