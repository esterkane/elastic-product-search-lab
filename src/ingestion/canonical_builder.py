"""Build complete product-search documents from canonical source state."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from src.ingestion.canonical_types import CanonicalBuildIssue, CanonicalBuildResult, SourceUpdate
from src.ingestion.search_profile import build_search_profile
from src.ingestion.source_state import ProductSourceState, utc_iso

MINIMUM_SEARCHABLE_FIELDS = frozenset({"product_id", "title", "brand", "category", "price", "currency", "availability", "seller_id"})


def build_canonical_product_document(
    state: ProductSourceState,
    indexed_at: datetime | None = None,
) -> CanonicalBuildResult:
    """Emit a complete indexable product document when minimum source state exists."""

    fields = state.merged_fields()
    missing = sorted(field for field in MINIMUM_SEARCHABLE_FIELDS if fields.get(field) in (None, ""))
    if missing:
        return CanonicalBuildResult(
            product_id=state.product_id,
            emitted=False,
            issues=[
                CanonicalBuildIssue(
                    code="canonical_product_incomplete",
                    message="Canonical product is missing required searchable field(s).",
                    retryable=True,
                    details={"missing_fields": missing},
                )
            ],
        )

    document: dict[str, Any] = {
        "product_id": state.product_id,
        "title": str(fields["title"]),
        "description": str(fields.get("description") or ""),
        "brand": str(fields["brand"]),
        "category": str(fields["category"]),
        "attributes": dict(fields.get("attributes") or {}),
        "price": float(fields["price"]),
        "currency": str(fields["currency"]).upper(),
        "availability": str(fields["availability"]),
        "popularity_score": float(fields.get("popularity_score") or 0),
        "seller_id": str(fields["seller_id"]),
        "source_versions": state.source_versions(),
        "updated_at": utc_iso(state.latest_updated_at() or datetime.now(timezone.utc)),
        "indexed_at": utc_iso(indexed_at or datetime.now(timezone.utc)),
    }
    document["catalog_text"] = build_catalog_text(document)
    document["search_profile"] = build_search_profile(document)

    return CanonicalBuildResult(product_id=state.product_id, emitted=True, document=deterministic_document(document))


def build_catalog_text(document: Mapping[str, Any]) -> str:
    attributes = document.get("attributes") if isinstance(document.get("attributes"), Mapping) else {}
    return " ".join(
        part
        for part in [
            str(document.get("title") or ""),
            str(document.get("description") or ""),
            str(document.get("brand") or ""),
            str(document.get("category") or ""),
            " ".join(str(value) for _, value in sorted(attributes.items())),
        ]
        if part
    )


def deterministic_document(document: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(document)
    if isinstance(normalized.get("attributes"), Mapping):
        normalized["attributes"] = dict(sorted(normalized["attributes"].items()))
    if isinstance(normalized.get("source_versions"), Mapping):
        normalized["source_versions"] = dict(sorted(normalized["source_versions"].items()))
    return normalized


def apply_source_update(state: ProductSourceState, update: SourceUpdate) -> CanonicalBuildResult:
    """Pure interface for replay workers or future Kafka consumers."""

    state.apply(update)
    return build_canonical_product_document(state)


def source_state_from_complete_product(
    product: Mapping[str, Any],
    *,
    source_version: str,
    indexed_source_name: str | None = "sample_jsonl",
) -> ProductSourceState:
    """Translate the existing complete JSONL product shape into source-owned state."""

    product_id = str(product["product_id"])
    updated_at = product.get("updated_at")
    if isinstance(updated_at, str):
        updated_at_value = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    elif isinstance(updated_at, datetime):
        updated_at_value = updated_at
    else:
        updated_at_value = None

    state = ProductSourceState(product_id=product_id)
    state.apply(
        SourceUpdate(
            source="catalog",
            product_id=product_id,
            source_version=source_version,
            updated_at=updated_at_value,
            fields={
                "title": product["title"],
                "description": product.get("description") or "",
                "brand": product["brand"],
                "category": product["category"],
                "attributes": dict(product.get("attributes") or {}),
                "seller_id": product["seller_id"],
            },
        )
    )
    state.apply(
        SourceUpdate(
            source="price",
            product_id=product_id,
            source_version=source_version,
            updated_at=updated_at_value,
            fields={"price": product["price"], "currency": product["currency"]},
        )
    )
    state.apply(
        SourceUpdate(
            source="inventory",
            product_id=product_id,
            source_version=source_version,
            updated_at=updated_at_value,
            fields={"availability": product["availability"]},
        )
    )
    state.apply(
        SourceUpdate(
            source="analytics",
            product_id=product_id,
            source_version=source_version,
            updated_at=updated_at_value,
            fields={"popularity_score": product["popularity_score"]},
        )
    )
    if indexed_source_name:
        state.extra_source_versions[indexed_source_name] = source_version
    return state

