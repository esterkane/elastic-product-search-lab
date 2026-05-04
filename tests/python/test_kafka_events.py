from datetime import datetime, timezone

import pytest

from src.ingestion.event_schema import ProductSourceEvent, SOURCE_TOPICS, parse_product_source_event
from src.ingestion.kafka_consumer import InMemoryStateStore, ListDlqSink, process_event, process_raw_event


class FakeIndexSink:
    def __init__(self):
        self.documents = []

    def index_product(self, product_id, document):
        self.documents.append((product_id, document))


def event(source, version, payload, product_id="P100001"):
    return ProductSourceEvent(
        source=source,
        event_type="snapshot",
        product_id=product_id,
        source_version=version,
        event_time=datetime(2026, 5, 1, 10, tzinfo=timezone.utc),
        payload=payload,
        trace_id=f"trace-{source}-{version}",
        correlation_id=f"corr-{product_id}",
    )


def complete_events(product_id="P100001"):
    return [
        event(
            "catalog",
            1,
            {
                "title": "Trail running shoes",
                "description": "Lightweight shoes for wet trails.",
                "brand": "Kaufland Sports",
                "category": "Sports > Running",
                "attributes": {"color": "blue", "terrain": "trail"},
                "seller_id": "seller-sports",
            },
            product_id=product_id,
        ),
        event("price", 1, {"price": 59.99, "currency": "eur"}, product_id=product_id),
        event("inventory", 1, {"availability": "in_stock"}, product_id=product_id),
        event("analytics", 1, {"popularity_score": 25.0}, product_id=product_id),
    ]


def test_product_source_event_schema_validates_topic_and_owned_fields():
    price = event("price", 3, {"price": 9.99, "currency": "eur"})

    assert price.topic() == SOURCE_TOPICS["price"]
    assert price.key() == "P100001"
    assert price.to_source_update().fields == {"price": 9.99, "currency": "eur"}

    with pytest.raises(ValueError, match="non-owned field"):
        event("price", 4, {"title": "not price owned"})


def test_consumer_out_of_order_events_do_not_corrupt_canonical_state():
    state_store = InMemoryStateStore()
    index_sink = FakeIndexSink()

    for item in complete_events():
        process_event(item, state_store=state_store, index_sink=index_sink)

    stale = event("inventory", 0, {"availability": "out_of_stock"})
    result = process_event(stale, state_store=state_store, index_sink=index_sink)

    assert result.outcome == "stale"
    assert index_sink.documents[-1][1]["availability"] == "in_stock"
    assert state_store.get("P100001").merged_fields()["availability"] == "in_stock"


def test_consumer_routes_malformed_events_to_dlq_without_crashing():
    state_store = InMemoryStateStore()
    index_sink = FakeIndexSink()
    dlq_sink = ListDlqSink()

    result = process_raw_event(
        b'{"source":"price","product_id":"P1","payload":{"title":"bad"}}',
        state_store=state_store,
        index_sink=index_sink,
        dlq_sink=dlq_sink,
        metadata={"topic": "product.price", "partition": 0, "offset": 10},
    )

    assert result.outcome == "dlq"
    assert result.error_kind == "non_retryable"
    assert dlq_sink.records[0]["code"] == "malformed_product_event"
    assert dlq_sink.records[0]["metadata"] == {"topic": "product.price", "partition": 0, "offset": 10}
    assert index_sink.documents == []


def test_parse_product_source_event_accepts_json_string():
    parsed = parse_product_source_event(event("inventory", 2, {"availability": "limited_stock"}).to_json_line())

    assert parsed.source == "inventory"
    assert parsed.payload == {"availability": "limited_stock"}

