"""Build a blue-green product index and atomically switch product aliases."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.create_index import build_client, ensure_reachable  # noqa: E402
from src.ingestion.bulk_indexer import bulk_index_products, configure_logging  # noqa: E402
from src.ingestion.models import Product  # noqa: E402
from src.search.index_management import (  # noqa: E402
    DEFAULT_PRODUCT_INDEX_PREFIX,
    DEFAULT_READ_ALIAS,
    DEFAULT_WRITE_ALIAS,
    create_product_index,
    install_product_index_resources,
    next_numeric_product_index_name,
    switch_product_aliases,
    versioned_product_index_name,
)

DEFAULT_REPLICAS = int(os.getenv("PRODUCT_INDEX_REPLICAS", "0"))
DEFAULT_SHARDS = int(os.getenv("PRODUCT_INDEX_SHARDS", "1"))


def iter_products(path: Path) -> list[Product]:
    products: list[Product] = []
    with path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            if not line.strip():
                continue
            try:
                products.append(Product.model_validate(json.loads(line)))
            except (json.JSONDecodeError, ValidationError) as exc:
                raise ValueError(f"Invalid product record on line {line_number}: {exc}") from exc
    return products


def list_product_indices(client: Any, *, prefix: str = DEFAULT_PRODUCT_INDEX_PREFIX) -> list[str]:
    try:
        response = client.indices.get(index=f"{prefix}-v*", features="_aliases")
    except Exception:  # noqa: BLE001 - no matching indices is a valid first-build state.
        return []
    if isinstance(response, dict):
        return sorted(response)
    return sorted(response.raw)  # elastic-transport ObjectApiResponse


def resolve_target_index(args: argparse.Namespace, client: Any) -> str:
    if args.target_index:
        return args.target_index
    if args.target_version:
        return versioned_product_index_name(args.target_version, prefix=args.index_prefix)
    return next_numeric_product_index_name(list_product_indices(client, prefix=args.index_prefix), prefix=args.index_prefix)


def reindex_source(client: Any, *, source_index: str, target_index: str) -> dict[str, Any]:
    return client.reindex(
        body={
            "conflicts": "proceed",
            "source": {"index": source_index},
            "dest": {"index": target_index, "op_type": "index"},
        },
        wait_for_completion=True,
        refresh=True,
        request_timeout=120,
    )


def load_jsonl_source(client: Any, *, input_path: Path, target_index: str, batch_size: int) -> dict[str, Any]:
    summary = bulk_index_products(client, iter_products(input_path), target_index, batch_size=batch_size)
    return {
        "indexed": summary.indexed_count,
        "failed": summary.failed_count,
        "retries": summary.retry_count,
        "elapsed_seconds": summary.elapsed_seconds,
    }


def run_smoke_checks(client: Any, *, target_index: str, min_docs: int) -> dict[str, Any]:
    if not client.indices.exists(index=target_index):
        raise RuntimeError(f"Smoke check failed: target index '{target_index}' does not exist.")

    count = int(client.count(index=target_index, query={"match_all": {}})["count"])
    if count < min_docs:
        raise RuntimeError(
            f"Smoke check failed: target index '{target_index}' has {count} docs, expected at least {min_docs}."
        )

    mapping = client.indices.get_mapping(index=target_index)
    mappings = next(iter(mapping.values())).get("mappings", {}) if mapping else {}
    properties = mappings.get("properties", {})
    for required_field in ("product_id", "catalog_text", "search_profile"):
        if required_field not in properties:
            raise RuntimeError(f"Smoke check failed: mapping missing '{required_field}'.")

    return {"target_index": target_index, "document_count": count, "required_fields": sorted(properties)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Blue-green product reindex/load and alias switch.")
    parser.add_argument("--source-index", default=DEFAULT_READ_ALIAS, help="Source index or alias for ES _reindex.")
    parser.add_argument("--input", type=Path, default=None, help="Optional JSONL product source to bulk load instead.")
    parser.add_argument("--target-index", default=None, help="Concrete target index. Defaults to next products-vN.")
    parser.add_argument("--target-version", default=None, help="Version suffix for products-v{version}.")
    parser.add_argument("--index-prefix", default=DEFAULT_PRODUCT_INDEX_PREFIX)
    parser.add_argument("--read-alias", default=DEFAULT_READ_ALIAS)
    parser.add_argument("--write-alias", default=DEFAULT_WRITE_ALIAS)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--min-docs", type=int, default=1)
    parser.add_argument("--shards", type=int, default=DEFAULT_SHARDS)
    parser.add_argument("--replicas", type=int, default=DEFAULT_REPLICAS)
    parser.add_argument("--install-resources", action="store_true")
    parser.add_argument("--recreate-target", action="store_true")
    parser.add_argument("--skip-smoke", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Build and smoke check only; do not switch aliases.")
    return parser.parse_args()


def main() -> int:
    configure_logging()
    args = parse_args()
    client = build_client()

    try:
        ensure_reachable(client)
        if args.install_resources:
            install_product_index_resources(client, shards=args.shards, replicas=args.replicas)
            print("Installed product pipeline/template and event/audit ILM/template resources.")

        target_index = resolve_target_index(args, client)
        create_product_index(
            client,
            target_index,
            recreate=args.recreate_target,
            shards=args.shards,
            replicas=args.replicas,
        )

        if args.input:
            load_result = load_jsonl_source(client, input_path=args.input, target_index=target_index, batch_size=args.batch_size)
        else:
            load_result = reindex_source(client, source_index=args.source_index, target_index=target_index)

        client.indices.refresh(index=target_index)
        smoke_result = None if args.skip_smoke else run_smoke_checks(client, target_index=target_index, min_docs=args.min_docs)
        alias_result = None
        if not args.dry_run:
            alias_result = switch_product_aliases(
                client,
                read_alias=args.read_alias,
                write_alias=args.write_alias,
                target_index=target_index,
            )

        print(
            json.dumps(
                {
                    "target_index": target_index,
                    "source_index": None if args.input else args.source_index,
                    "input": str(args.input) if args.input else None,
                    "load_result": load_result,
                    "smoke_result": smoke_result,
                    "alias_result": alias_result,
                    "dry_run": args.dry_run,
                },
                indent=2,
                sort_keys=True,
            )
        )
    except Exception as exc:  # noqa: BLE001 - deployment scripts should fail loudly with context.
        print(json.dumps({"error": str(exc), "retryable": False, "stage": "reindex_and_switch"}, sort_keys=True), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
