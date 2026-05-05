from datetime import datetime, timezone
from random import Random

from src.ingestion.event_schema import INDEXER_TOPIC_CONTRACTS, ProductSourceEvent
from src.ingestion.kafka_consumer import (
    BulkElasticsearchIndexSink,
    InMemoryStateStore,
    IndexerCounters,
    ListDlqSink,
    ProductEventIndexer,
)


class FakeBulkClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.operations = []

    def bulk(self, operations):
        self.operations.append(operations)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def bulk_response(status=201, error=None):
    result = {"status": status}
    if error:
        result["error"] = error
    return {"items": [{"index": result}]}


def event(source, version, payload, *, product_id="P100001", event_type="upsert"):
    return ProductSourceEvent(
        source=source,
        event_type=event_type,
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
                "attributes": {"color": "blue"},
                "seller_id": "seller-sports",
            },
            product_id=product_id,
        ),
        event("price", 1, {"price": 59.99, "currency": "eur"}, product_id=product_id),
        event("inventory", 1, {"availability": "in_stock"}, product_id=product_id),
        event("analytics", 1, {"popularity_score": 25.0}, product_id=product_id),
    ]


def make_indexer(client):
    counters = IndexerCounters()
    return ProductEventIndexer(
        state_store=InMemoryStateStore(),
        index_sink=BulkElasticsearchIndexSink(
            client,
            "products-build",
            counters=counters,
            sleep=lambda _: None,
            rng=Random(7),
        ),
        dlq_sink=ListDlqSink(),
        counters=counters,
    )


def test_indexer_topic_contracts_include_requested_lab_topics():
    assert INDEXER_TOPIC_CONTRACTS["product-change"] == ("catalog", "seller")
    assert INDEXER_TOPIC_CONTRACTS["price-stock"] == ("price", "inventory", "stock")
    assert INDEXER_TOPIC_CONTRACTS["merchandising"] == ("merchandising", "analytics")
    assert INDEXER_TOPIC_CONTRACTS["delete"] == ("lifecycle",)


def test_replay_uses_idempotent_bulk_writes_and_skips_duplicate_delivery():
    client = FakeBulkClient([bulk_response(), bulk_response(), bulk_response()])
    indexer = make_indexer(client)

    for offset, item in enumerate(complete_events()):
        indexer.process_raw(
            item.to_json_line(),
            metadata={"topic": item.topic(), "partition": 0, "offset": offset},
            replay=True,
        )
    duplicate = complete_events()[3]
    result = indexer.process_raw(
        duplicate.to_json_line(),
        metadata={"topic": duplicate.topic(), "partition": 0, "offset": 3},
        replay=True,
    )

    assert result.code == "duplicate_message"
    assert indexer.counters.processed == 5
    assert indexer.counters.indexed == 2
    assert indexer.counters.incomplete == 2
    assert indexer.counters.duplicate == 1
    assert client.operations[-1][0] == {"index": {"_index": "products-build", "_id": "P100001"}}
    assert client.operations[-1][1]["product_id"] == "P100001"


def test_out_of_order_events_and_duplicate_source_versions_do_not_corrupt_state():
    client = FakeBulkClient([bulk_response(), bulk_response()])
    indexer = make_indexer(client)
    for offset, item in enumerate(complete_events()):
        indexer.process_raw(item.to_json_line(), metadata={"topic": item.topic(), "partition": 0, "offset": offset})

    stale_price = event("price", 0, {"price": 999.99, "currency": "usd"})
    result = indexer.process_raw(
        stale_price.to_json_line(),
        metadata={"topic": stale_price.topic(), "partition": 0, "offset": 9},
    )

    assert result.outcome == "stale"
    assert indexer.state_store.get("P100001").merged_fields()["price"] == 59.99
    assert client.operations[-1][1]["price"] == 59.99


def test_tombstone_can_emit_minimal_soft_delete_document():
    client = FakeBulkClient([bulk_response()])
    indexer = make_indexer(client)
    tombstone = event(
        "lifecycle",
        5,
        {
            "is_deleted": True,
            "deleted_at": "2026-05-01T12:00:00Z",
            "delete_reason": "source_tombstone",
        },
        product_id="P-deleted",
        event_type="delete",
    )

    result = indexer.process_raw(tombstone.to_json_line(), metadata={"topic": "delete", "partition": 0, "offset": 1})

    assert result.outcome == "indexed"
    assert client.operations[0][0] == {"index": {"_index": "products-build", "_id": "P-deleted"}}
    assert client.operations[0][1]["is_deleted"] is True
    assert "title" not in client.operations[0][1]


def test_bulk_sink_retries_429_with_exponential_backoff_counter():
    client = FakeBulkClient([bulk_response(429, "too_many_requests"), bulk_response(201)])
    delays = []
    counters = IndexerCounters()
    sink = BulkElasticsearchIndexSink(
        client,
        "products-build",
        counters=counters,
        sleep=delays.append,
        rng=Random(0),
        initial_backoff_seconds=0.5,
        jitter_seconds=0,
    )

    sink.index_product("P100001", {"product_id": "P100001"})

    assert len(client.operations) == 2
    assert delays == [0.5]
    assert counters.retries == 1


def test_409_conflict_is_non_retryable_and_sent_to_dlq():
    client = FakeBulkClient([bulk_response(), bulk_response(409, "version_conflict")])
    indexer = make_indexer(client)
    for offset, item in enumerate(complete_events()):
        indexer.process_raw(item.to_json_line(), metadata={"topic": item.topic(), "partition": 0, "offset": offset})
    newer_price = event("price", 2, {"price": 54.99, "currency": "eur"})

    indexer.process_raw(
        newer_price.to_json_line(),
        metadata={"topic": newer_price.topic(), "partition": 0, "offset": 4},
    )

    assert indexer.counters.dlq == 1
    assert indexer.counters.conflicts == 1
    assert indexer.dlq_sink.records[0]["code"] == "index_conflict"
    assert indexer.dlq_sink.records[0]["metadata"]["status"] == 409
