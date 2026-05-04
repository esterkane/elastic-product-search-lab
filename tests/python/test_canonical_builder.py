from datetime import datetime, timezone

import pytest

from src.ingestion.canonical_builder import build_canonical_product_document, source_state_from_complete_product
from src.ingestion.canonical_types import SourceUpdate
from src.ingestion.source_state import ProductSourceState


def catalog_update(version: int = 1, **fields):
    payload = {
        "title": "Organic coffee beans",
        "description": "Medium roast whole beans.",
        "brand": "Kaufland Bio",
        "category": "Grocery > Coffee",
        "attributes": {"origin": "Colombia", "roast": "medium"},
        "seller_id": "kaufland",
    }
    payload.update(fields)
    return SourceUpdate(
        source="catalog",
        product_id="P100001",
        source_version=version,
        updated_at=datetime(2026, 5, 1, 10, tzinfo=timezone.utc),
        fields=payload,
    )


def price_update(version: int = 1, **fields):
    payload = {"price": 8.99, "currency": "eur"}
    payload.update(fields)
    return SourceUpdate(
        source="price",
        product_id="P100001",
        source_version=version,
        updated_at=datetime(2026, 5, 1, 11, tzinfo=timezone.utc),
        fields=payload,
    )


def inventory_update(version: int = 1, **fields):
    payload = {"availability": "in_stock"}
    payload.update(fields)
    return SourceUpdate(
        source="inventory",
        product_id="P100001",
        source_version=version,
        updated_at=datetime(2026, 5, 1, 12, tzinfo=timezone.utc),
        fields=payload,
    )


def analytics_update(version: int = 1, **fields):
    payload = {"popularity_score": 42.0}
    payload.update(fields)
    return SourceUpdate(
        source="analytics",
        product_id="P100001",
        source_version=version,
        updated_at=datetime(2026, 5, 1, 13, tzinfo=timezone.utc),
        fields=payload,
    )


def complete_state() -> ProductSourceState:
    state = ProductSourceState(product_id="P100001")
    for update in [catalog_update(), price_update(), inventory_update(), analytics_update()]:
        assert state.apply(update) is True
    return state


def test_source_ownership_does_not_overwrite_unrelated_fields():
    state = ProductSourceState(product_id="P100001")
    state.apply(catalog_update(title="Original catalog title"))
    state.apply(price_update(price=7.49))

    state.apply(price_update(version=2, price=6.99))

    document = build_canonical_product_document(state)
    assert document.emitted is False
    assert state.merged_fields()["title"] == "Original catalog title"
    assert state.merged_fields()["price"] == 6.99

    with pytest.raises(ValueError, match="non-owned field"):
        state.apply(price_update(version=3, title="Price source must not own title"))


def test_newer_source_versions_replace_older_versions_only_for_that_source():
    state = complete_state()

    assert state.apply(price_update(version=0, price=99.99)) is False
    assert state.apply(price_update(version=2, price=6.49)) is True

    result = build_canonical_product_document(state, indexed_at=datetime(2026, 5, 2, tzinfo=timezone.utc))

    assert result.emitted is True
    assert result.document is not None
    assert result.document["price"] == 6.49
    assert result.document["title"] == "Organic coffee beans"
    assert result.document["source_versions"]["price"] == "2"
    assert result.document["source_versions"]["catalog"] == "1"


def test_incomplete_products_are_not_emitted_as_searchable_documents():
    state = ProductSourceState(product_id="P100001")
    state.apply(catalog_update())

    result = build_canonical_product_document(state)

    assert result.emitted is False
    assert result.document is None
    assert result.issues[0].code == "canonical_product_incomplete"
    assert result.issues[0].retryable is True
    assert result.issues[0].details["missing_fields"] == ["availability", "currency", "price"]


def test_canonical_builder_output_is_deterministic_for_same_input_state():
    indexed_at = datetime(2026, 5, 2, tzinfo=timezone.utc)
    first = build_canonical_product_document(complete_state(), indexed_at=indexed_at)
    second = build_canonical_product_document(complete_state(), indexed_at=indexed_at)

    assert first.document == second.document
    assert first.document is not None
    assert first.document["catalog_text"] == (
        "Organic coffee beans Medium roast whole beans. Kaufland Bio Grocery > Coffee Colombia medium"
    )
    assert first.document["search_profile"].startswith("Product: Organic coffee beans.")


def test_existing_complete_sample_product_shape_builds_valid_index_document():
    state = source_state_from_complete_product(
        {
            "product_id": "P-sample",
            "title": "Wireless mouse",
            "description": "Quiet ergonomic mouse.",
            "brand": "Logi",
            "category": "Computer Accessories",
            "attributes": {"color": "black", "product_locale": "de"},
            "price": 19.99,
            "currency": "eur",
            "availability": "limited_stock",
            "popularity_score": 12.5,
            "seller_id": "seller-1",
            "updated_at": "2026-05-01T10:00:00Z",
        },
        source_version="2026-05-01T10:00:00Z",
    )

    result = build_canonical_product_document(state, indexed_at=datetime(2026, 5, 2, tzinfo=timezone.utc))

    assert result.emitted is True
    assert result.document is not None
    assert result.document["product_id"] == "P-sample"
    assert result.document["currency"] == "EUR"
    assert result.document["source_versions"] == {
        "analytics": "2026-05-01T10:00:00Z",
        "catalog": "2026-05-01T10:00:00Z",
        "inventory": "2026-05-01T10:00:00Z",
        "price": "2026-05-01T10:00:00Z",
        "sample_jsonl": "2026-05-01T10:00:00Z",
    }

