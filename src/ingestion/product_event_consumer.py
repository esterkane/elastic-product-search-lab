"""Apply product catalog change events to deterministic Elasticsearch documents."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from elasticsearch import NotFoundError

from src.ingestion.events import ProductEvent

LOGGER = logging.getLogger(__name__)
EventResult = Literal["updated", "skipped_stale", "failed"]


@dataclass(frozen=True)
class EventReplaySummary:
    processed: int
    updated: int
    skipped_stale: int
    failed: int
    elapsed_seconds: float


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(level=level, format="%(message)s")


def log_event(event: str, **fields: Any) -> None:
    LOGGER.info(json.dumps({"event": event, **fields}, sort_keys=True))


def utc_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def event_partial_document(event: ProductEvent, indexed_at: datetime | None = None) -> dict[str, Any]:
    """Build the mapped partial document fields changed by an event."""

    document: dict[str, Any] = {
        "updated_at": utc_timestamp(event.event_time),
        "indexed_at": utc_timestamp(indexed_at or datetime.now(timezone.utc)),
    }

    if event.event_type == "product_title_updated":
        document["title"] = str(event.payload["title"])
    elif event.event_type == "product_category_updated":
        document["category"] = str(event.payload["category"])
    elif event.event_type == "product_availability_updated":
        document["availability"] = str(event.payload["availability"])
    elif event.event_type == "product_price_updated":
        document["price"] = float(event.payload["price"])
        if "currency" in event.payload:
            document["currency"] = str(event.payload["currency"]).upper()
    elif event.event_type == "seller_enrichment_updated":
        for field in ("seller_id", "brand", "popularity_score"):
            if field in event.payload:
                document[field] = event.payload[field]
    elif event.event_type == "attributes_updated":
        document["attributes"] = dict(event.payload["attributes"])
    elif event.event_type == "product_deleted_or_unavailable":
        document["availability"] = str(event.payload.get("availability", "discontinued"))

    return document


def parse_source_version(value: Any) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def source_version_is_stale(existing_versions: dict[str, Any], event: ProductEvent) -> bool:
    current = parse_source_version(existing_versions.get(event.source_system))
    return current is not None and current >= event.source_version


def merged_source_versions(existing_versions: dict[str, Any], event: ProductEvent) -> dict[str, Any]:
    merged = dict(existing_versions)
    merged[event.source_system] = str(event.source_version)
    return merged


def fetch_source_versions(client: Any, index_name: str, product_id: str) -> dict[str, Any] | None:
    try:
        response = client.get(index=index_name, id=product_id, _source_includes=["source_versions"])
    except NotFoundError:
        return None

    source = response.get("_source", {})
    versions = source.get("source_versions", {})
    return versions if isinstance(versions, dict) else {}


def apply_event(client: Any, index_name: str, event: ProductEvent, indexed_at: datetime | None = None) -> EventResult:
    existing_versions = fetch_source_versions(client, index_name, event.product_id)
    if existing_versions is None:
        log_event("product_event_missing_document", event_id=event.event_id, product_id=event.product_id)
        return "failed"

    if source_version_is_stale(existing_versions, event):
        log_event(
            "product_event_skipped_stale",
            event_id=event.event_id,
            product_id=event.product_id,
            source_system=event.source_system,
            source_version=event.source_version,
            existing_source_version=existing_versions.get(event.source_system),
        )
        return "skipped_stale"

    document = event_partial_document(event, indexed_at=indexed_at)
    document["source_versions"] = merged_source_versions(existing_versions, event)

    try:
        client.update(index=index_name, id=event.product_id, doc=document, retry_on_conflict=3)
    except Exception as exc:  # noqa: BLE001 - keep replay moving and report failed events.
        log_event("product_event_update_failed", event_id=event.event_id, product_id=event.product_id, error=str(exc))
        return "failed"

    log_event(
        "product_event_updated",
        event_id=event.event_id,
        product_id=event.product_id,
        source_system=event.source_system,
        source_version=event.source_version,
    )
    return "updated"


def apply_events(client: Any, index_name: str, events: list[ProductEvent]) -> EventReplaySummary:
    started_at = time.perf_counter()
    updated = 0
    skipped_stale = 0
    failed = 0

    for event in events:
        result = apply_event(client, index_name, event)
        if result == "updated":
            updated += 1
        elif result == "skipped_stale":
            skipped_stale += 1
        else:
            failed += 1

    return EventReplaySummary(
        processed=len(events),
        updated=updated,
        skipped_stale=skipped_stale,
        failed=failed,
        elapsed_seconds=time.perf_counter() - started_at,
    )
