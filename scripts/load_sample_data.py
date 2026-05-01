"""Load deterministic sample product data into Elasticsearch."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.create_index import build_client, create_index, ensure_reachable  # noqa: E402
from src.ingestion.bulk_indexer import bulk_index_products, configure_logging  # noqa: E402
from src.ingestion.models import Product  # noqa: E402

DEFAULT_INDEX = "products-v1"
DEFAULT_SAMPLE_PATH = PROJECT_ROOT / "data" / "sample" / "products.jsonl"


def load_products(path: Path) -> list[Product]:
    products: list[Product] = []
    with path.open("r", encoding="utf-8") as sample_file:
        for line_number, line in enumerate(sample_file, start=1):
            if not line.strip():
                continue
            try:
                products.append(Product.model_validate(json.loads(line)))
            except (json.JSONDecodeError, ValidationError) as exc:
                raise ValueError(f"Invalid product record on line {line_number}: {exc}") from exc
    return products


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load sample products into Elasticsearch.")
    parser.add_argument("--batch-size", type=int, default=10, help="Bulk indexing batch size.")
    parser.add_argument("--index", default=os.getenv("PRODUCT_INDEX", DEFAULT_INDEX))
    parser.add_argument("--sample-path", type=Path, default=DEFAULT_SAMPLE_PATH)
    return parser.parse_args()


def main() -> int:
    configure_logging()
    args = parse_args()
    client = build_client()

    try:
        ensure_reachable(client)
        create_index(client, args.index, recreate=False)
        products = load_products(args.sample_path)
        summary = bulk_index_products(client, products, args.index, batch_size=args.batch_size)
        client.indices.refresh(index=args.index)
        count = client.count(index=args.index, query={"match_all": {}})["count"]
        print(
            "Indexed sample products: "
            f"indexed={summary.indexed_count} failed={summary.failed_count} "
            f"retries={summary.retry_count} elapsed_seconds={summary.elapsed_seconds:.3f}"
        )
        print(f"Sample query result count: {count}")
    except Exception as exc:  # noqa: BLE001 - script should print a clear failure and exit non-zero.
        print(f"Sample data load failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())