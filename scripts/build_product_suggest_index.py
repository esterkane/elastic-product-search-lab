"""Build a separate autocomplete index from canonical product snapshots."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.create_index import build_client, ensure_reachable  # noqa: E402
from src.search.index_management import DEFAULT_SUGGEST_INDEX, product_suggest_index_body  # noqa: E402

DEFAULT_INPUT = PROJECT_ROOT / "data" / "sample" / "products.jsonl"
DEFAULT_REPLICAS = int(os.getenv("PRODUCT_INDEX_REPLICAS", "0"))
DEFAULT_SHARDS = int(os.getenv("PRODUCT_INDEX_SHARDS", "1"))


def iter_snapshots(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid product snapshot on line {line_number}: {exc}") from exc
    return records


def suggest_document(product: dict[str, Any]) -> dict[str, Any]:
    parts = [
        str(product.get("title") or ""),
        str(product.get("brand") or ""),
        str(product.get("category") or ""),
    ]
    return {
        "product_id": str(product["product_id"]),
        "suggest_text": " ".join(part for part in parts if part),
        "title": str(product.get("title") or ""),
        "brand": str(product.get("brand") or ""),
        "category": str(product.get("category") or ""),
        "popularity_score": float(product.get("popularity_score") or 0),
        "updated_at": str(product.get("updated_at") or "1970-01-01T00:00:00Z"),
    }


def build_operations(products: list[dict[str, Any]], index_name: str) -> list[dict[str, Any]]:
    operations: list[dict[str, Any]] = []
    for product in products:
        product_id = str(product["product_id"])
        operations.append({"index": {"_index": index_name, "_id": product_id}})
        operations.append(suggest_document(product))
    return operations


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build product-suggest from canonical product snapshots.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--index", default=os.getenv("PRODUCT_SUGGEST_INDEX", DEFAULT_SUGGEST_INDEX))
    parser.add_argument("--recreate", action="store_true", help="Delete and recreate the suggest index before loading.")
    parser.add_argument("--shards", type=int, default=DEFAULT_SHARDS)
    parser.add_argument("--replicas", type=int, default=DEFAULT_REPLICAS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = build_client()
    try:
        ensure_reachable(client)
        if client.indices.exists(index=args.index) and args.recreate:
            client.indices.delete(index=args.index)
        if not client.indices.exists(index=args.index):
            client.indices.create(index=args.index, body=product_suggest_index_body(shards=args.shards, replicas=args.replicas))
        products = iter_snapshots(args.input)
        response = client.bulk(operations=build_operations(products, args.index))
        failed = sum(1 for item in response.get("items", []) if int(item.get("index", {}).get("status", 500)) >= 300)
        client.indices.refresh(index=args.index)
    except Exception as exc:  # noqa: BLE001 - script should print a clear local failure.
        print(f"Suggest index build failed: {exc}", file=sys.stderr)
        return 1

    print(f"indexed={len(products) - failed}")
    print(f"failed={failed}")
    print(f"index={args.index}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
