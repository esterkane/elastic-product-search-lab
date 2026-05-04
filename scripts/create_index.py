"""Create product search indices and optional index-management resources."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from elasticsearch import ApiError, ConnectionError, TransportError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX = "products-v1"
DEFAULT_URL = "http://localhost:9200"
DEFAULT_REPLICAS = int(os.getenv("PRODUCT_INDEX_REPLICAS", "0"))
DEFAULT_SHARDS = int(os.getenv("PRODUCT_INDEX_SHARDS", "1"))

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.search.index_management import (  # noqa: E402
    DEFAULT_BUILD_ALIAS,
    DEFAULT_READ_ALIAS,
    create_product_index,
    install_product_index_resources,
    point_build_alias,
    utc_build_id,
    versioned_product_index_name,
)


def build_client() -> Elasticsearch:
    load_dotenv(PROJECT_ROOT / ".env")
    url = os.getenv("ELASTICSEARCH_URL", DEFAULT_URL)

    # Local Docker disables security. Opt in to basic auth only when a secured
    # cluster is used outside the default demo runtime.
    use_auth = os.getenv("ELASTICSEARCH_USE_AUTH", "false").lower() in {"1", "true", "yes"}
    username = os.getenv("ELASTICSEARCH_USERNAME")
    password = os.getenv("ELASTICSEARCH_PASSWORD")

    client_options: dict[str, Any] = {"request_timeout": 10}
    if use_auth and username and password:
        client_options["basic_auth"] = (username, password)

    return Elasticsearch(url, **client_options)


def ensure_reachable(client: Elasticsearch) -> None:
    try:
        info = client.info()
    except ConnectionError as exc:
        raise RuntimeError(
            f"Elasticsearch is not reachable. Start it with scripts/dev-up.ps1 and retry. Details: {exc}"
        ) from exc
    except TransportError as exc:
        raise RuntimeError(f"Could not connect to Elasticsearch cleanly: {exc}") from exc

    version = info.get("version", {}).get("number", "unknown")
    cluster_name = info.get("cluster_name", "unknown")
    print(f"Connected to Elasticsearch {version} on cluster '{cluster_name}'.")


def create_index(
    client: Elasticsearch,
    index_name: str,
    recreate: bool,
    *,
    shards: int = DEFAULT_SHARDS,
    replicas: int = DEFAULT_REPLICAS,
) -> None:
    exists = client.indices.exists(index=index_name)
    if exists and recreate:
        print(f"Deleting existing index '{index_name}' because --recreate was passed.")
    if exists and not recreate:
        print(f"Index '{index_name}' already exists. No changes applied.")
        return

    create_product_index(client, index_name, recreate=recreate, shards=shards, replicas=replicas)
    print(f"Created index '{index_name}'.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create the Elasticsearch product index.")
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Delete the existing product index before creating it again.",
    )
    parser.add_argument(
        "--index",
        default=os.getenv("PRODUCT_INDEX", DEFAULT_INDEX),
        help="Index name. Defaults to PRODUCT_INDEX or products-v1.",
    )
    parser.add_argument("--build-id", default=None, help="Build id for a versioned products-v{build_id} index.")
    parser.add_argument(
        "--install-resources",
        action="store_true",
        help="Install product ingest pipeline, product index template, and event/audit ILM/template resources.",
    )
    parser.add_argument("--shards", type=int, default=DEFAULT_SHARDS, help="Primary shard count for lab indices.")
    parser.add_argument("--replicas", type=int, default=DEFAULT_REPLICAS, help="Replica count for lab indices.")
    parser.add_argument("--read-alias", default=DEFAULT_READ_ALIAS, help="Read alias name for staged builds.")
    parser.add_argument("--build-alias", default=DEFAULT_BUILD_ALIAS, help="Build alias name for staged builds.")
    parser.add_argument(
        "--point-build-alias",
        action="store_true",
        help="Point the build alias at the created versioned index.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = build_client()

    try:
        ensure_reachable(client)
        if args.install_resources:
            install_product_index_resources(client, shards=args.shards, replicas=args.replicas)
            print("Installed product pipeline/template and event/audit ILM/template resources.")
        index_name = versioned_product_index_name(args.build_id or utc_build_id()) if args.build_id else args.index
        create_index(client, index_name, args.recreate, shards=args.shards, replicas=args.replicas)
        if args.point_build_alias:
            point_build_alias(client, build_alias=args.build_alias, target_index=index_name)
            print(f"Pointed build alias '{args.build_alias}' at '{index_name}'.")
    except (ApiError, RuntimeError) as exc:
        print(f"Index creation failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
