"""Kafka-compatible product event schema for canonical ingestion."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.ingestion.canonical_types import SOURCE_OWNED_FIELDS, SourceName, SourceUpdate

KafkaEventType = Literal["snapshot", "upsert", "delete", "unavailable"]

SOURCE_TOPICS: dict[SourceName, str] = {
    "catalog": "product.catalog",
    "price": "product.price",
    "inventory": "product.inventory",
    "reviews": "product.reviews",
    "analytics": "product.analytics",
}
DLQ_TOPIC = "product.dlq"
ALL_PRODUCT_TOPICS: tuple[str, ...] = tuple(SOURCE_TOPICS.values())


class ProductSourceEvent(BaseModel):
    """Versioned source event safe for Kafka, Redpanda, or JSONL fixtures."""

    model_config = ConfigDict(extra="forbid")

    source: SourceName
    event_type: KafkaEventType
    product_id: str = Field(min_length=1)
    source_version: int | str
    event_time: datetime
    payload: dict[str, Any] = Field(default_factory=dict)
    trace_id: str | None = None
    correlation_id: str | None = None

    @field_validator("event_time")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("event_time must include a timezone")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_source_owned_payload(self) -> "ProductSourceEvent":
        unknown = set(self.payload) - SOURCE_OWNED_FIELDS[self.source]
        if unknown:
            fields = ", ".join(sorted(unknown))
            raise ValueError(f"{self.source} event contains non-owned field(s): {fields}")
        if self.event_type in {"snapshot", "upsert"} and not self.payload:
            raise ValueError(f"{self.event_type} events must include a non-empty payload")
        return self

    def topic(self) -> str:
        return SOURCE_TOPICS[self.source]

    def key(self) -> str:
        return self.product_id

    def to_source_update(self) -> SourceUpdate:
        return SourceUpdate(
            source=self.source,
            product_id=self.product_id,
            source_version=self.source_version,
            updated_at=self.event_time,
            fields=dict(self.payload),
        )

    def to_json_line(self) -> str:
        return json.dumps(self.model_dump(mode="json", exclude_none=True), sort_keys=True)


def parse_product_source_event(raw: bytes | str | dict[str, Any]) -> ProductSourceEvent:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    if isinstance(raw, str):
        raw = json.loads(raw)
    return ProductSourceEvent.model_validate(raw)


def load_product_source_events(path: Path) -> list[ProductSourceEvent]:
    events: list[ProductSourceEvent] = []
    with path.open("r", encoding="utf-8") as event_file:
        for line_number, line in enumerate(event_file, start=1):
            if not line.strip():
                continue
            try:
                events.append(parse_product_source_event(line))
            except Exception as exc:  # noqa: BLE001 - include fixture line context.
                raise ValueError(f"Invalid canonical product event on line {line_number}: {exc}") from exc
    return events

