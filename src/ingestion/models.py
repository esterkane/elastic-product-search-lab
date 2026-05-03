"""Pydantic models for product ingestion."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.ingestion.search_profile import build_search_profile

Availability = Literal["in_stock", "limited_stock", "backorder", "out_of_stock", "discontinued"]


class Product(BaseModel):
    """Validated product record accepted by the ingestion pipeline."""

    model_config = ConfigDict(extra="forbid")

    product_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(default="")
    brand: str = Field(min_length=1)
    category: str = Field(min_length=1)
    attributes: dict[str, Any] = Field(default_factory=dict)
    price: float = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    availability: Availability
    popularity_score: float = Field(ge=0)
    seller_id: str = Field(min_length=1)
    updated_at: datetime

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @field_validator("updated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("updated_at must include a timezone")
        return value.astimezone(timezone.utc)

    def to_index_document(self, indexed_at: datetime | None = None) -> dict[str, Any]:
        indexed_timestamp = indexed_at or datetime.now(timezone.utc)
        document = self.model_dump(mode="json")
        document["catalog_text"] = " ".join(
            part
            for part in [
                self.title,
                self.description,
                self.brand,
                self.category,
                " ".join(str(value) for value in self.attributes.values()),
            ]
            if part
        )
        document["search_profile"] = build_search_profile(document)
        document["source_versions"] = {
            "sample_jsonl": self.updated_at.isoformat().replace("+00:00", "Z")
        }
        document["indexed_at"] = indexed_timestamp.isoformat().replace("+00:00", "Z")
        return document
