"""Deterministic bulk indexing utilities for product documents."""

from __future__ import annotations

import json
import logging
import random
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from elasticsearch import ConnectionError

from src.ingestion.models import Product

LOGGER = logging.getLogger(__name__)
RETRYABLE_STATUSES = {429, 503}


@dataclass(frozen=True)
class BulkIndexSummary:
    indexed_count: int
    failed_count: int
    retry_count: int
    elapsed_seconds: float


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(level=level, format="%(message)s")


def log_event(event: str, **fields: Any) -> None:
    LOGGER.info(json.dumps({"event": event, **fields}, sort_keys=True))


def chunked(items: Sequence[Product], batch_size: int) -> Iterable[list[Product]]:
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    for start in range(0, len(items), batch_size):
        yield list(items[start : start + batch_size])


def product_document_id(product: Product) -> str:
    return product.product_id


def build_bulk_operations(
    products: Sequence[Product], index_name: str, indexed_at: datetime | None = None
) -> list[dict[str, Any]]:
    operations: list[dict[str, Any]] = []
    timestamp = indexed_at or datetime.now(timezone.utc)

    for product in products:
        operations.append({"index": {"_index": index_name, "_id": product_document_id(product)}})
        operations.append(product.to_index_document(indexed_at=timestamp))

    return operations


def _is_retryable_exception(exc: Exception) -> bool:
    return isinstance(exc, ConnectionError) or getattr(exc, "status_code", None) in RETRYABLE_STATUSES


def _split_bulk_result(
    products: Sequence[Product], response: dict[str, Any]
) -> tuple[list[Product], int, int]:
    retryable_products: list[Product] = []
    indexed_count = 0
    failed_count = 0

    for product, item in zip(products, response.get("items", []), strict=False):
        result = item.get("index", {})
        status = int(result.get("status", 500))

        if 200 <= status < 300:
            indexed_count += 1
        elif status in RETRYABLE_STATUSES:
            retryable_products.append(product)
        else:
            failed_count += 1
            log_event("bulk_item_failed", product_id=product.product_id, status=status, error=result.get("error"))

    failed_count += max(0, len(products) - len(response.get("items", [])))
    return retryable_products, indexed_count, failed_count


def bulk_index_products(
    client: Any,
    products: Sequence[Product],
    index_name: str,
    batch_size: int = 100,
    max_retries: int = 3,
    initial_backoff_seconds: float = 0.25,
    jitter_seconds: float = 0.1,
    sleep: Callable[[float], None] = time.sleep,
    rng: random.Random | None = None,
) -> BulkIndexSummary:
    """Index products with deterministic IDs and bounded transient retries."""

    started_at = time.perf_counter()
    random_source = rng or random.Random()
    indexed_count = 0
    failed_count = 0
    retry_count = 0

    for batch in chunked(list(products), batch_size):
        pending = batch
        attempt = 0

        while pending:
            try:
                response = client.bulk(operations=build_bulk_operations(pending, index_name))
            except Exception as exc:  # noqa: BLE001 - classify client transport failures here.
                if _is_retryable_exception(exc) and attempt < max_retries:
                    retry_count += 1
                    delay = initial_backoff_seconds * (2**attempt) + random_source.uniform(0, jitter_seconds)
                    log_event("bulk_retry_exception", attempt=attempt + 1, delay_seconds=delay, error=str(exc))
                    sleep(delay)
                    attempt += 1
                    continue
                failed_count += len(pending)
                log_event("bulk_batch_failed", count=len(pending), error=str(exc))
                break

            retryable_products, batch_indexed, batch_failed = _split_bulk_result(pending, response)
            indexed_count += batch_indexed
            failed_count += batch_failed

            if retryable_products and attempt < max_retries:
                retry_count += 1
                delay = initial_backoff_seconds * (2**attempt) + random_source.uniform(0, jitter_seconds)
                log_event("bulk_retry_items", attempt=attempt + 1, retryable_count=len(retryable_products), delay_seconds=delay)
                sleep(delay)
                pending = retryable_products
                attempt += 1
                continue

            if retryable_products:
                failed_count += len(retryable_products)
                for product in retryable_products:
                    log_event("bulk_item_failed_after_retries", product_id=product.product_id)
            break

    summary = BulkIndexSummary(indexed_count, failed_count, retry_count, time.perf_counter() - started_at)
    log_event("bulk_index_summary", **summary.__dict__)
    return summary