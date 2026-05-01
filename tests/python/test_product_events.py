from datetime import datetime, timezone

from pydantic import ValidationError

from src.ingestion.events import ProductEvent
from src.ingestion.product_event_consumer import (
    apply_event,
    event_partial_document,
    merged_source_versions,
    source_version_is_stale,
)


def make_event(**overrides):
    data = {
        "event_id": "evt-1",
        "product_id": "P100001",
        "source_system": "catalog_content",
        "event_type": "product_title_updated",
        "event_time": "2026-05-01T10:00:00Z",
        "payload": {"title": "Updated ergonomic wireless mouse"},
        "source_version": 11,
    }
    data.update(overrides)
    return ProductEvent.model_validate(data)


def test_product_event_validation_requires_timezone_and_payload():
    valid = make_event()
    assert valid.event_time.tzinfo is not None

    try:
        make_event(event_time="2026-05-01T10:00:00")
    except ValidationError:
        pass
    else:
        raise AssertionError("event_time without timezone should fail validation")

    try:
        make_event(payload={})
    except ValidationError:
        pass
    else:
        raise AssertionError("title update without title should fail validation")


def test_partial_update_generation_sets_business_and_ingestion_timestamps():
    event = make_event()
    indexed_at = datetime(2026, 5, 1, 10, 0, 3, tzinfo=timezone.utc)

    document = event_partial_document(event, indexed_at=indexed_at)

    assert document["title"] == "Updated ergonomic wireless mouse"
    assert document["updated_at"] == "2026-05-01T10:00:00Z"
    assert document["indexed_at"] == "2026-05-01T10:00:03Z"


def test_delete_or_unavailable_event_defaults_to_discontinued():
    event = make_event(
        event_type="product_deleted_or_unavailable",
        payload={},
        source_system="inventory_service",
        source_version=42,
    )

    document = event_partial_document(event)

    assert document["availability"] == "discontinued"


def test_source_version_stale_detection_and_merge():
    event = make_event(source_system="inventory_service", source_version=8)
    existing = {"inventory_service": "10", "catalog_content": "3"}

    assert source_version_is_stale(existing, event) is True
    assert merged_source_versions(existing, make_event(source_system="pricing_service", source_version=4)) == {
        "inventory_service": "10",
        "catalog_content": "3",
        "pricing_service": "4",
    }


class FakeEventClient:
    def __init__(self, source_versions):
        self.source_versions = source_versions
        self.updates = []

    def get(self, **kwargs):
        return {"_source": {"source_versions": self.source_versions}}

    def update(self, **kwargs):
        self.updates.append(kwargs)
        return {"result": "updated"}


def test_apply_event_skips_stale_version_without_update():
    client = FakeEventClient({"inventory_service": "88"})
    event = make_event(source_system="inventory_service", source_version=80)

    assert apply_event(client, "products-v1", event) == "skipped_stale"
    assert client.updates == []


def test_apply_event_updates_with_merged_source_versions():
    client = FakeEventClient({"catalog_content": "10", "pricing_service": "55"})
    event = make_event(source_system="catalog_content", source_version=12)

    assert apply_event(client, "products-v1", event, indexed_at=datetime(2026, 5, 1, tzinfo=timezone.utc)) == "updated"
    update = client.updates[0]
    assert update["index"] == "products-v1"
    assert update["id"] == "P100001"
    assert update["retry_on_conflict"] == 3
    assert update["doc"]["source_versions"] == {"catalog_content": "12", "pricing_service": "55"}
