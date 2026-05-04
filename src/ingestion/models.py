"""Pydantic models for product ingestion."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.ingestion.canonical_builder import build_canonical_product_document, source_state_from_complete_product

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
        source_version = self.updated_at.isoformat().replace("+00:00", "Z")
        state = source_state_from_complete_product(
            self.model_dump(mode="python"),
            source_version=source_version,
        )
        result = build_canonical_product_document(state, indexed_at=indexed_at)
        if not result.emitted or result.document is None:
            raise ValueError(f"Product {self.product_id} cannot produce an index document: {result.issues}")
        return result.document
