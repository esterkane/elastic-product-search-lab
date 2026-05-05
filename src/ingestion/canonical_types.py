"""Canonical product document types and source ownership rules."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SourceName = Literal["catalog", "seller", "price", "stock", "inventory", "reviews", "analytics", "merchandising", "lifecycle"]
SourceClock = int | str
Availability = Literal["in_stock", "limited_stock", "backorder", "out_of_stock", "discontinued"]

SOURCE_OWNED_FIELDS: dict[SourceName, frozenset[str]] = {
    "catalog": frozenset({"title", "description", "brand", "category", "attributes", "seller_id"}),
    "seller": frozenset({"seller", "seller_id", "seller_name", "seller_rating", "is_marketplace"}),
    "price": frozenset({"price", "currency"}),
    "stock": frozenset({"stock", "availability", "stock_quantity", "warehouse_id"}),
    "inventory": frozenset({"availability"}),
    "reviews": frozenset({"average_rating", "review_count"}),
    "analytics": frozenset({"popularity_score"}),
    "merchandising": frozenset({"merchandising", "badges", "boost_tags", "campaign_ids", "cohort_tags"}),
    "lifecycle": frozenset({"lifecycle", "is_deleted", "deleted_at", "delete_reason"}),
}

INDEXED_PRODUCT_FIELDS = frozenset(
    {
        "product_id",
        "schema_version",
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
        "seller",
        "stock",
        "price_info",
        "offers",
        "merchandising",
        "lifecycle",
        "is_deleted",
        "deleted_at",
        "cohort_tags",
        "updated_at",
        "catalog_text",
        "search_profile",
        "source_versions",
        "source_attribution",
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
