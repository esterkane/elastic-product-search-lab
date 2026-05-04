"""Load deterministic sample product data into Elasticsearch."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Iterator
from pathlib import Path

from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.create_index import build_client, create_index, ensure_reachable  # noqa: E402
from src.ingestion.bulk_indexer import bulk_index_products, configure_logging  # noqa: E402
from src.ingestion.models import Product  # noqa: E402
from src.search.index_management import (  # noqa: E402
    DEFAULT_BUILD_ALIAS,
    DEFAULT_READ_ALIAS,
    install_product_index_resources,
    point_build_alias,
    switch_read_alias,
    utc_build_id,
    versioned_product_index_name,
)

DEFAULT_INDEX = "products-v1"
DEFAULT_SAMPLE_PATH = PROJECT_ROOT / "data" / "sample" / "products.jsonl"
DEFAULT_REPLICAS = int(os.getenv("PRODUCT_INDEX_REPLICAS", "0"))
DEFAULT_SHARDS = int(os.getenv("PRODUCT_INDEX_SHARDS", "1"))


def load_products(path: Path) -> list[Product]:
    return list(iter_products(path))


def iter_products(path: Path) -> Iterator[Product]:
    with path.open("r", encoding="utf-8") as sample_file:
        for line_number, line in enumerate(sample_file, start=1):
            if not line.strip():
                continue
            try:
                yield Product.model_validate(json.loads(line))
            except (json.JSONDecodeError, ValidationError) as exc:
                raise ValueError(f"Invalid product record on line {line_number}: {exc}") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load sample products into Elasticsearch.")
    parser.add_argument("--batch-size", type=int, default=10, help="Bulk indexing batch size.")
    parser.add_argument("--index", default=os.getenv("PRODUCT_INDEX", DEFAULT_INDEX))
    parser.add_argument("--input", "--sample-path", dest="input", type=Path, default=DEFAULT_SAMPLE_PATH)
    parser.add_argument("--build-id", default=None, help="Build id for a versioned products-v{build_id} staging index.")
    parser.add_argument("--staging-index", default=None, help="Explicit concrete staging index name.")
    parser.add_argument("--install-resources", action="store_true", help="Install product/event templates, ILM, and pipeline.")
    parser.add_argument("--switch-alias", action="store_true", help="Switch products-read to the loaded staging index after validation.")
    parser.add_argument("--read-alias", default=DEFAULT_READ_ALIAS)
    parser.add_argument("--build-alias", default=DEFAULT_BUILD_ALIAS)
    parser.add_argument("--shards", type=int, default=DEFAULT_SHARDS)
    parser.add_argument("--replicas", type=int, default=DEFAULT_REPLICAS)
    return parser.parse_args()


def resolve_target_index(args: argparse.Namespace) -> str:
    if args.staging_index:
        return args.staging_index
    if args.build_id:
        return versioned_product_index_name(args.build_id)
    if args.switch_alias:
        return versioned_product_index_name(utc_build_id())
    return args.index


def main() -> int:
    configure_logging()
    args = parse_args()
    client = build_client()

    try:
        ensure_reachable(client)
        if args.install_resources:
            install_product_index_resources(client, shards=args.shards, replicas=args.replicas)
            print("Installed product pipeline/template and event/audit ILM/template resources.")
        target_index = resolve_target_index(args)
        create_index(client, target_index, recreate=False, shards=args.shards, replicas=args.replicas)
        if args.staging_index or args.build_id or args.switch_alias:
            point_build_alias(client, build_alias=args.build_alias, target_index=target_index)
        products = iter_products(args.input)
        summary = bulk_index_products(client, products, target_index, batch_size=args.batch_size)
        client.indices.refresh(index=target_index)
        count = client.count(index=target_index, query={"match_all": {}})["count"]
        if args.switch_alias:
            switch_read_alias(client, read_alias=args.read_alias, target_index=target_index)
        print(
            "Indexed sample products: "
            f"indexed={summary.indexed_count} failed={summary.failed_count} "
            f"retries={summary.retry_count} elapsed_seconds={summary.elapsed_seconds:.3f}"
        )
        print(f"Sample query result count: {count}")
        print(f"Target index: {target_index}")
        if args.switch_alias:
            print(f"Read alias '{args.read_alias}' now points at '{target_index}'.")
    except Exception as exc:  # noqa: BLE001 - script should print a clear failure and exit non-zero.
        print(f"Sample data load failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
