import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.ingestion.canonical_builder import build_canonical_product_document, source_state_from_complete_product
from src.ingestion.canonical_types import SourceUpdate
from src.ingestion.source_state import ProductSourceState

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "canonical"


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


def seller_update(version: int = 1, **fields):
    payload = {"seller_name": "Kaufland", "seller_rating": 4.8, "is_marketplace": False}
    payload.update(fields)
    return SourceUpdate(
        source="seller",
        product_id="P100001",
        source_version=version,
        updated_at=datetime(2026, 5, 1, 9, tzinfo=timezone.utc),
        fields=payload,
    )


def stock_update(version: int = 1, **fields):
    payload = {"availability": "limited_stock", "stock_quantity": 7, "warehouse_id": "berlin-1"}
    payload.update(fields)
    return SourceUpdate(
        source="stock",
        product_id="P100001",
        source_version=version,
        updated_at=datetime(2026, 5, 1, 12, tzinfo=timezone.utc),
        fields=payload,
    )


def merchandising_update(version: int = 1, **fields):
    payload = {"badges": ["bio"], "boost_tags": ["coffee-week"], "campaign_ids": ["spring"], "cohort_tags": ["loyalty"]}
    payload.update(fields)
    return SourceUpdate(
        source="merchandising",
        product_id="P100001",
        source_version=version,
        updated_at=datetime(2026, 5, 1, 14, tzinfo=timezone.utc),
        fields=payload,
    )


def lifecycle_update(version: int = 1, **fields):
    payload = {"is_deleted": False}
    payload.update(fields)
    return SourceUpdate(
        source="lifecycle",
        product_id="P100001",
        source_version=version,
        updated_at=datetime(2026, 5, 1, 15, tzinfo=timezone.utc),
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
    assert first.document["schema_version"] == "catalog-v2"
    assert first.document["source_attribution"]["title"] == "catalog@1"
    assert first.document["source_attribution"]["price_info"] == "price@1"


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


def test_canonical_document_merges_production_catalog_state():
    state = complete_state()
    state.apply(seller_update())
    state.apply(stock_update())
    state.apply(merchandising_update())
    state.apply(lifecycle_update())

    result = build_canonical_product_document(state, indexed_at=datetime(2026, 5, 2, tzinfo=timezone.utc))

    assert result.emitted is True
    assert result.document is not None
    assert result.document["seller"] == {
        "seller_id": "kaufland",
        "seller_name": "Kaufland",
        "seller_rating": 4.8,
        "is_marketplace": False,
    }
    assert result.document["stock"] == {
        "availability": "limited_stock",
        "stock_quantity": 7,
        "warehouse_id": "berlin-1",
    }
    assert result.document["price_info"] == {"amount": 8.99, "currency": "EUR"}
    assert result.document["offers"] == [
        {
            "offer_id": "P100001:kaufland",
            "seller_id": "kaufland",
            "price": 8.99,
            "currency": "EUR",
            "availability": "limited_stock",
            "stock_quantity": 7,
            "is_buy_box": True,
        }
    ]
    assert result.document["merchandising"] == {
        "badges": ["bio"],
        "boost_tags": ["coffee-week"],
        "campaign_ids": ["spring"],
    }
    assert result.document["lifecycle"]["is_deleted"] is False
    assert result.document["is_deleted"] is False
    assert result.document["cohort_tags"] == ["loyalty"]
    assert result.document["autosuggest"] == "Organic coffee beans Kaufland Bio Grocery > Coffee"


def test_out_of_order_fixture_rebuild_is_idempotent_and_ignores_stale_versions():
    events = [
        SourceUpdate.model_validate_json(line)
        for line in (FIXTURE_DIR / "out_of_order_events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    first_state = ProductSourceState(product_id="P100001")
    second_state = ProductSourceState(product_id="P100001")
    accepted = [first_state.apply(event) for event in events]
    for event in events:
        second_state.apply(event)

    indexed_at = datetime(2026, 5, 2, tzinfo=timezone.utc)
    first = build_canonical_product_document(first_state, indexed_at=indexed_at)
    second = build_canonical_product_document(second_state, indexed_at=indexed_at)

    assert accepted == [True, True, True, True, False]
    assert first.document == second.document
    assert first.document is not None
    assert first.document["price"] == 7.49
    assert first.document["currency"] == "EUR"
    assert first.document["source_versions"]["price"] == "2"
    assert "_debug" not in first.document["attributes"]


def test_soft_delete_tombstone_emits_minimal_non_searchable_document():
    state = ProductSourceState(product_id="P-deleted")
    state.apply(
        SourceUpdate(
            source="lifecycle",
            product_id="P-deleted",
            source_version=5,
            updated_at=datetime(2026, 5, 1, 16, tzinfo=timezone.utc),
            fields={
                "is_deleted": True,
                "deleted_at": "2026-05-01T16:00:00Z",
                "delete_reason": "source_tombstone",
            },
        )
    )

    result = build_canonical_product_document(state, indexed_at=datetime(2026, 5, 2, tzinfo=timezone.utc))

    assert result.emitted is True
    assert result.document is not None
    assert result.document["product_id"] == "P-deleted"
    assert result.document["is_deleted"] is True
    assert result.document["lifecycle"]["delete_reason"] == "source_tombstone"
    assert result.document["source_versions"] == {"lifecycle": "5"}
    assert "title" not in result.document
    assert result.issues == []


def test_source_hygiene_removes_transient_source_fields_from_nested_source():
    state = complete_state()
    state.apply(
        merchandising_update(
            merchandising={"badges": ["bio"], "_tmp": {"unsafe": True}, "debug": "drop"},
            badges=["bio"],
        )
    )

    result = build_canonical_product_document(state, indexed_at=datetime(2026, 5, 2, tzinfo=timezone.utc))

    assert result.emitted is True
    serialized = json.dumps(result.document, sort_keys=True)
    assert "_tmp" not in serialized
    assert "raw_event" not in serialized
