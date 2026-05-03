from datetime import datetime, timezone
from random import Random

from elasticsearch import ConnectionError
from pydantic import ValidationError

from src.ingestion.bulk_indexer import build_bulk_operations, bulk_index_products, product_document_id
from src.ingestion.models import Product


def make_product(product_id: str = "P-test-001") -> Product:
    return Product.model_validate(
        {
            "product_id": product_id,
            "title": "Test Product",
            "description": "A deterministic test product.",
            "brand": "TestBrand",
            "category": "Test > Products",
            "attributes": {"color": "black", "product_locale": "us"},
            "price": 19.99,
            "currency": "usd",
            "availability": "in_stock",
            "popularity_score": 10.5,
            "seller_id": "seller-test",
            "updated_at": "2026-04-20T10:15:00Z",
        }
    )


def test_product_model_normalizes_currency_and_requires_timezone():
    product = make_product()
    assert product.currency == "USD"

    invalid = make_product().model_dump(mode="json")
    invalid["updated_at"] = "2026-04-20T10:15:00"

    try:
        Product.model_validate(invalid)
    except ValidationError:
        pass
    else:
        raise AssertionError("Product without timezone should fail validation")


def test_document_id_is_deterministic_product_id():
    assert product_document_id(make_product("P-stable-id")) == "P-stable-id"


def test_bulk_action_generation_uses_index_and_source_document():
    product = make_product("P-action-001")
    indexed_at = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)

    operations = build_bulk_operations([product], "products-v1", indexed_at=indexed_at)

    assert operations[0] == {"index": {"_index": "products-v1", "_id": "P-action-001"}}
    assert operations[1]["product_id"] == "P-action-001"
    assert operations[1]["catalog_text"].startswith("Test Product")
    assert operations[1]["search_profile"].startswith("Product: Test Product.")
    assert operations[1]["indexed_at"] == "2026-05-01T12:00:00Z"
    assert operations[1]["source_versions"]["sample_jsonl"] == "2026-04-20T10:15:00Z"


class FakeBulkClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def bulk(self, operations):
        self.calls.append(operations)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def successful_response(count: int):
    return {"errors": False, "items": [{"index": {"status": 201}} for _ in range(count)]}


def test_bulk_index_products_reports_success_summary():
    client = FakeBulkClient([successful_response(2)])
    summary = bulk_index_products(
        client, [make_product("P-1"), make_product("P-2")], "products-v1", batch_size=10, sleep=lambda _: None
    )

    assert summary.indexed_count == 2
    assert summary.failed_count == 0
    assert summary.retry_count == 0
    assert len(client.calls) == 1


def test_bulk_index_products_retries_transient_item_status():
    client = FakeBulkClient(
        [
            {"errors": True, "items": [{"index": {"status": 429, "error": {"type": "too_many_requests"}}}]},
            successful_response(1),
        ]
    )
    summary = bulk_index_products(
        client, [make_product("P-retry")], "products-v1", batch_size=1, sleep=lambda _: None, rng=Random(7)
    )

    assert summary.indexed_count == 1
    assert summary.failed_count == 0
    assert summary.retry_count == 1
    assert len(client.calls) == 2


def test_bulk_index_products_does_not_retry_mapping_errors():
    client = FakeBulkClient(
        [
            {
                "errors": True,
                "items": [
                    {"index": {"status": 400, "error": {"type": "mapper_parsing_exception"}}}
                ],
            }
        ]
    )
    summary = bulk_index_products(client, [make_product("P-bad")], "products-v1", batch_size=1, sleep=lambda _: None)

    assert summary.indexed_count == 0
    assert summary.failed_count == 1
    assert summary.retry_count == 0
    assert len(client.calls) == 1


def test_bulk_index_products_retries_connection_errors():
    client = FakeBulkClient([ConnectionError("temporary outage"), successful_response(1)])
    summary = bulk_index_products(
        client, [make_product("P-connection")], "products-v1", batch_size=1, sleep=lambda _: None, rng=Random(3)
    )

    assert summary.indexed_count == 1
    assert summary.failed_count == 0
    assert summary.retry_count == 1
    assert len(client.calls) == 2
