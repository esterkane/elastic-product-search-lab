"""Canonical product document types and source ownership rules."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SourceName = Literal["catalog", "price", "inventory", "reviews", "analytics"]
SourceClock = int | str
Availability = Literal["in_stock", "limited_stock", "backorder", "out_of_stock", "discontinued"]

SOURCE_OWNED_FIELDS: dict[SourceName, frozenset[str]] = {
    "catalog": frozenset({"title", "description", "brand", "category", "attributes", "seller_id"}),
    "price": frozenset({"price", "currency"}),
    "inventory": frozenset({"availability"}),
    "reviews": frozenset({"average_rating", "review_count"}),
    "analytics": frozenset({"popularity_score"}),
}

INDEXED_PRODUCT_FIELDS = frozenset(
    {
        "product_id",
        "title",
        "description",
        "brand",
        "category",
        "attributes",
        "price",
        "currency",
        "availability",
        "popularity_score",
        "seller_id",
        "cohort_tags",
        "updated_at",
        "catalog_text",
        "search_profile",
        "source_versions",
        "indexed_at",
    }
)


class SourceUpdate(BaseModel):
    """A versioned update owned by one upstream product-data source."""

    model_config = ConfigDict(extra="forbid")

    source: SourceName
    product_id: str = Field(min_length=1)
    source_version: SourceClock
    updated_at: datetime | None = None
    fields: dict[str, Any] = Field(default_factory=dict)

    @field_validator("updated_at")
    @classmethod
    def normalize_updated_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("updated_at must include a timezone")
        return value.astimezone(timezone.utc)

    @field_validator("fields")
    @classmethod
    def copy_fields(cls, value: Mapping[str, Any]) -> dict[str, Any]:
        return dict(value)


class CanonicalBuildIssue(BaseModel):
    """Structured reason a source state cannot produce a searchable document."""

    code: str
    message: str
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class CanonicalBuildResult(BaseModel):
    """Canonical builder result for future batch, replay, or Kafka callers."""

    product_id: str
    emitted: bool
    document: dict[str, Any] | None = None
    issues: list[CanonicalBuildIssue] = Field(default_factory=list)
