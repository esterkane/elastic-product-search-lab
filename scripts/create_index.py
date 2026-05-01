"""Create the product search index for the local Elasticsearch lab."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from elasticsearch import ApiError, ConnectionError, TransportError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAPPING_PATH = PROJECT_ROOT / "src" / "search" / "product_mapping.json"
DEFAULT_INDEX = "products-v1"
DEFAULT_URL = "http://localhost:9200"


def load_mapping() -> dict[str, Any]:
    with MAPPING_PATH.open("r", encoding="utf-8") as mapping_file:
        return json.load(mapping_file)


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


def create_index(client: Elasticsearch, index_name: str, recreate: bool) -> None:
    mapping = load_mapping()
    exists = client.indices.exists(index=index_name)

    if exists and recreate:
        print(f"Deleting existing index '{index_name}' because --recreate was passed.")
        client.indices.delete(index=index_name)
        exists = False

    if exists:
        print(f"Index '{index_name}' already exists. No changes applied.")
        return

    client.indices.create(index=index_name, **mapping)
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = build_client()

    try:
        ensure_reachable(client)
        create_index(client, args.index, args.recreate)
    except (ApiError, RuntimeError) as exc:
        print(f"Index creation failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
