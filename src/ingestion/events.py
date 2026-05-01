"""Validated product catalog change events."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ProductEventType = Literal[
    "product_title_updated",
    "product_category_updated",
    "product_availability_updated",
    "product_price_updated",
    "seller_enrichment_updated",
    "attributes_updated",
    "product_deleted_or_unavailable",
]

REQUIRED_PAYLOAD_FIELDS: dict[str, set[str]] = {
    "product_title_updated": {"title"},
    "product_category_updated": {"category"},
    "product_availability_updated": {"availability"},
    "product_price_updated": {"price"},
    "seller_enrichment_updated": set(),
    "attributes_updated": {"attributes"},
    "product_deleted_or_unavailable": set(),
}


class ProductEvent(BaseModel):
    """A single upstream catalog event for one product document."""

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1)
    product_id: str = Field(min_length=1)
    source_system: str = Field(min_length=1)
    event_type: ProductEventType
    event_time: datetime
    payload: dict[str, Any] = Field(default_factory=dict)
    source_version: int = Field(ge=0)

    @field_validator("event_time")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("event_time must include a timezone")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_payload_for_event_type(self) -> "ProductEvent":
        missing = REQUIRED_PAYLOAD_FIELDS[self.event_type] - self.payload.keys()
        if missing:
            fields = ", ".join(sorted(missing))
            raise ValueError(f"{self.event_type} payload is missing required field(s): {fields}")

        if self.event_type == "attributes_updated" and not isinstance(self.payload.get("attributes"), dict):
            raise ValueError("attributes_updated payload.attributes must be an object")
        if self.event_type == "product_price_updated" and float(self.payload["price"]) < 0:
            raise ValueError("product_price_updated payload.price must be non-negative")
        return self


def load_events(path: Path) -> list[ProductEvent]:
    events: list[ProductEvent] = []
    with path.open("r", encoding="utf-8") as events_file:
        for line_number, line in enumerate(events_file, start=1):
            if not line.strip():
                continue
            try:
                events.append(ProductEvent.model_validate(json.loads(line)))
            except Exception as exc:  # noqa: BLE001 - include line context for operators.
                raise ValueError(f"Invalid product event on line {line_number}: {exc}") from exc
    return events
