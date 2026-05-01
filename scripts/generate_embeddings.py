"""Generate and bulk-update dense vector embeddings for product documents."""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.create_index import build_client, ensure_reachable  # noqa: E402
from scripts.load_sample_data import load_products  # noqa: E402
from src.embeddings.embedder import EMBEDDING_DIMS, batched, build_embedding_text, get_embedder  # noqa: E402

DEFAULT_INDEX = "products-v1"
DEFAULT_INPUT = PROJECT_ROOT / "data" / "sample" / "products.jsonl"
RETRYABLE_STATUSES = {429, 503}


def load_products_from_es(client: Any, index_name: str, size: int = 1000) -> list[dict[str, Any]]:
    response = client.search(index=index_name, size=size, query={"match_all": {}})
    return [dict(hit.get("_source", {}), product_id=hit.get("_id")) for hit in response.get("hits", {}).get("hits", [])]


def bulk_update_embeddings(client: Any, index_name: str, updates: list[tuple[str, list[float]]], max_retries: int = 3) -> tuple[int, int, int]:
    pending = updates
    indexed = 0
    failed = 0
    retries = 0
    attempt = 0
    rng = random.Random(11)

    while pending:
        operations: list[dict[str, Any]] = []
        for product_id, vector in pending:
            operations.append({"update": {"_index": index_name, "_id": product_id}})
            operations.append({"doc": {"embedding": vector}})
        try:
            response = client.bulk(operations=operations)
        except Exception as exc:  # noqa: BLE001 - classify transient transport failures here.
            if attempt < max_retries:
                retries += 1
                delay = 0.25 * (2**attempt) + rng.uniform(0, 0.1)
                print(f"bulk embedding update failed transiently; retrying in {delay:.2f}s: {exc}")
                time.sleep(delay)
                attempt += 1
                continue
            return indexed, failed + len(pending), retries

        retryable: list[tuple[str, list[float]]] = []
        for update, item in zip(pending, response.get("items", []), strict=False):
            status = int(item.get("update", {}).get("status", 500))
            if 200 <= status < 300:
                indexed += 1
            elif status in RETRYABLE_STATUSES:
                retryable.append(update)
            else:
                failed += 1
                print(f"embedding update failed for {update[0]}: {item.get('update', {}).get('error')}")
        failed += max(0, len(pending) - len(response.get("items", [])))
        if retryable and attempt < max_retries:
            retries += 1
            delay = 0.25 * (2**attempt) + rng.uniform(0, 0.1)
            time.sleep(delay)
            pending = retryable
            attempt += 1
            continue
        failed += len(retryable)
        break
    return indexed, failed, retries


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate local product embeddings and update Elasticsearch docs.")
    parser.add_argument("--index", default=os.getenv("PRODUCT_INDEX", DEFAULT_INDEX))
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Product JSONL input. Use --from-es to read existing docs instead.")
    parser.add_argument("--from-es", action="store_true", help="Load products from Elasticsearch instead of JSONL.")
    parser.add_argument("--provider", choices=["auto", "sentence-transformers", "hash"], default="auto")
    parser.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--batch-size", type=int, default=32)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = build_client()
    try:
        ensure_reachable(client)
        products = load_products_from_es(client, args.index) if args.from_es else [p.to_index_document() for p in load_products(args.input)]
        embedder = get_embedder(args.provider, args.model)
        updates: list[tuple[str, list[float]]] = []
        for batch in batched(products, args.batch_size):
            texts = [build_embedding_text(product) for product in batch]
            vectors = embedder.encode(texts)
            for product, vector in zip(batch, vectors, strict=True):
                if len(vector) != EMBEDDING_DIMS:
                    raise ValueError(f"Expected {EMBEDDING_DIMS} dimensions, got {len(vector)}")
                updates.append((str(product["product_id"]), vector))
        indexed, failed, retries = bulk_update_embeddings(client, args.index, updates)
        client.indices.refresh(index=args.index)
        print(f"Embedding update summary: indexed={indexed} failed={failed} retries={retries}")
    except Exception as exc:  # noqa: BLE001 - CLI should fail clearly.
        print(f"Embedding generation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())