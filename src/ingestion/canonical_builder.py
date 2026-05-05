"""Build complete product-search documents from canonical source state."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from src.ingestion.canonical_types import CanonicalBuildIssue, CanonicalBuildResult, SourceUpdate
from src.ingestion.search_profile import build_search_profile
from src.ingestion.source_state import ProductSourceState, utc_iso

MINIMUM_SEARCHABLE_FIELDS = frozenset({"product_id", "title", "brand", "category", "price", "currency", "availability", "seller_id"})
CANONICAL_SCHEMA_VERSION = "catalog-v2"
TRANSIENT_SOURCE_KEYS = frozenset({"_debug", "_tmp", "debug", "raw_event", "trace"})


def build_canonical_product_document(
    state: ProductSourceState,
    indexed_at: datetime | None = None,
) -> CanonicalBuildResult:
    """Emit a complete indexable product document when minimum source state exists."""

    fields = state.merged_fields()
    lifecycle = dict(fields.get("lifecycle") or {})
    is_deleted = bool(lifecycle.get("is_deleted", fields.get("is_deleted", False)))
    deleted_at = lifecycle.get("deleted_at", fields.get("deleted_at"))
    missing = sorted(field for field in MINIMUM_SEARCHABLE_FIELDS if fields.get(field) in (None, ""))
    if missing and not is_deleted:
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
    if missing and is_deleted:
        field_attribution = state.source_attribution()
        return CanonicalBuildResult(
            product_id=state.product_id,
            emitted=True,
            document=deterministic_document(
                {
                    "schema_version": CANONICAL_SCHEMA_VERSION,
                    "product_id": state.product_id,
                    "lifecycle": {
                        "is_deleted": True,
                        "deleted_at": deleted_at,
                        "delete_reason": str(lifecycle.get("delete_reason") or fields.get("delete_reason") or "tombstone"),
                    },
                    "is_deleted": True,
                    "deleted_at": deleted_at,
                    "source_versions": state.source_versions(),
                    "source_attribution": attribution_for_document(
                        state,
                        {"lifecycle": field_attribution.get("lifecycle", field_attribution.get("is_deleted", "lifecycle"))},
                    ),
                    "updated_at": utc_iso(state.latest_updated_at() or datetime.now(timezone.utc)),
                    "indexed_at": utc_iso(indexed_at or datetime.now(timezone.utc)),
                }
            ),
        )

    attributes = clean_attribute_bag(fields.get("attributes") or {})
    seller_id = str(fields["seller_id"])
    seller_fields = dict(fields.get("seller") or {})
    seller = {
        "seller_id": str(seller_fields.get("seller_id") or fields.get("seller_id") or seller_id),
        "seller_name": str(seller_fields.get("seller_name") or fields.get("seller_name") or seller_id),
        "seller_rating": float(seller_fields.get("seller_rating") or fields.get("seller_rating") or 0),
        "is_marketplace": bool(seller_fields.get("is_marketplace", fields.get("is_marketplace", seller_id != "kaufland"))),
    }
    stock_fields = dict(fields.get("stock") or {})
    stock = {
        "availability": str(stock_fields.get("availability") or fields["availability"]),
        "stock_quantity": int(stock_fields.get("stock_quantity") or fields.get("stock_quantity") or 0),
        "warehouse_id": str(stock_fields.get("warehouse_id") or fields.get("warehouse_id") or "default"),
    }
    price_info = {
        "amount": float(fields["price"]),
        "currency": str(fields["currency"]).upper(),
    }
    merchandising = dict(fields.get("merchandising") or {})
    badges = fields.get("badges", merchandising.get("badges", []))
    boost_tags = fields.get("boost_tags", merchandising.get("boost_tags", []))
    campaign_ids = fields.get("campaign_ids", merchandising.get("campaign_ids", []))
    cohort_tags = sorted(
        {
            str(tag).lower()
            for tag in [
                *(attributes.get("cohort_tags", []) if isinstance(attributes.get("cohort_tags"), list) else []),
                *(fields.get("cohort_tags", []) if isinstance(fields.get("cohort_tags"), list) else []),
                *(merchandising.get("cohort_tags", []) if isinstance(merchandising.get("cohort_tags"), list) else []),
            ]
            if str(tag).strip()
        }
    )
    field_attribution = state.source_attribution()
    document: dict[str, Any] = {
        "schema_version": CANONICAL_SCHEMA_VERSION,
        "product_id": state.product_id,
        "title": str(fields["title"]),
        "description": str(fields.get("description") or ""),
        "brand": str(fields["brand"]),
        "category": str(fields["category"]),
        "attributes": attributes,
        "price": float(fields["price"]),
        "currency": str(fields["currency"]).upper(),
        "availability": str(fields["availability"]),
        "popularity_score": float(fields.get("popularity_score") or 0),
        "seller_id": seller_id,
        "seller": seller,
        "stock": stock,
        "price_info": price_info,
        "offers": [
            {
                "offer_id": f"{state.product_id}:{seller['seller_id']}",
                "seller_id": seller["seller_id"],
                "price": price_info["amount"],
                "currency": price_info["currency"],
                "availability": stock["availability"],
                "stock_quantity": stock["stock_quantity"],
                "is_buy_box": True,
            }
        ],
        "merchandising": {
            "badges": sorted(str(value) for value in badges if str(value).strip()) if isinstance(badges, list) else [],
            "boost_tags": sorted(str(value) for value in boost_tags if str(value).strip()) if isinstance(boost_tags, list) else [],
            "campaign_ids": sorted(str(value) for value in campaign_ids if str(value).strip()) if isinstance(campaign_ids, list) else [],
        },
        "lifecycle": {
            "is_deleted": is_deleted,
            "deleted_at": deleted_at,
            "delete_reason": str(lifecycle.get("delete_reason") or fields.get("delete_reason") or ""),
        },
        "is_deleted": is_deleted,
        "deleted_at": deleted_at,
        "cohort_tags": cohort_tags,
        "source_versions": state.source_versions(),
        "source_attribution": attribution_for_document(
            state,
            {
                "autosuggest": "builder:derived",
                "catalog_text": "builder:derived",
                "offers": "builder:canonical",
                "price_info": field_attribution.get("price", "builder:canonical"),
                "search_profile": "builder:derived",
                "schema_version": "builder:canonical",
                "seller": field_attribution.get("seller", field_attribution.get("seller_id", "builder:canonical")),
                "stock": field_attribution.get("stock", field_attribution.get("availability", "builder:canonical")),
            },
        ),
        "updated_at": utc_iso(state.latest_updated_at() or datetime.now(timezone.utc)),
        "indexed_at": utc_iso(indexed_at or datetime.now(timezone.utc)),
    }
    document["autosuggest"] = build_autosuggest_text(document)
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


def build_autosuggest_text(document: Mapping[str, Any]) -> str:
    return " ".join(
        part
        for part in [
            str(document.get("title") or ""),
            str(document.get("brand") or ""),
            str(document.get("category") or ""),
        ]
        if part
    )


def deterministic_document(document: Mapping[str, Any]) -> dict[str, Any]:
    normalized = clean_source_value(dict(document))
    if isinstance(normalized.get("attributes"), Mapping):
        normalized["attributes"] = dict(sorted(normalized["attributes"].items()))
    if isinstance(normalized.get("source_versions"), Mapping):
        normalized["source_versions"] = dict(sorted(normalized["source_versions"].items()))
    if isinstance(normalized.get("source_attribution"), Mapping):
        normalized["source_attribution"] = dict(sorted(normalized["source_attribution"].items()))
    if isinstance(normalized.get("merchandising"), Mapping):
        normalized["merchandising"] = {
            key: sorted(value) if isinstance(value, list) else value
            for key, value in sorted(normalized["merchandising"].items())
        }
    if isinstance(normalized.get("cohort_tags"), list):
        normalized["cohort_tags"] = sorted(normalized["cohort_tags"])
    if normalized.get("deleted_at") is None:
        normalized["deleted_at"] = None
    return normalized


def attribution_for_document(state: ProductSourceState, derived_fields: Mapping[str, str] | None = None) -> dict[str, str]:
    attribution = state.source_attribution()
    attribution.update(dict(derived_fields or {}))
    return dict(sorted(attribution.items()))


def clean_attribute_bag(attributes: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(key): clean_source_value(value)
        for key, value in sorted(attributes.items())
        if key not in TRANSIENT_SOURCE_KEYS and not str(key).startswith("_") and value is not None
    }


def clean_source_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): clean_source_value(child)
            for key, child in sorted(value.items())
            if key not in TRANSIENT_SOURCE_KEYS and not str(key).startswith("_")
        }
    if isinstance(value, list):
        return [clean_source_value(child) for child in value if child is not None]
    return value


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
