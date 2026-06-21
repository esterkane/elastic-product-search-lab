"""Unit tests for the MCP tool handlers.

These call the pure handlers directly with a fake Elasticsearch client — no live
services. They assert input validation, the structured-error shape (category /
retryable / no stack trace), the shaped success payload, and that
`list_strategies` reports the real strategy names.
"""

from __future__ import annotations

from typing import Any

from src.mcp.tools import list_strategies_impl, product_search_impl
from src.search.strategies import STRATEGY_NAMES

# --- fakes ----------------------------------------------------------------


class FakeES:
    """Minimal Elasticsearch stand-in for the handler's .search call."""

    def __init__(self, *, hits: list[dict[str, Any]] | None = None, search_error: Exception | None = None) -> None:
        self._hits = hits if hits is not None else []
        self._search_error = search_error
        self.search_calls: list[dict[str, Any]] = []

    def search(self, **kwargs: Any) -> dict[str, Any]:
        self.search_calls.append(kwargs)
        if self._search_error is not None:
            raise self._search_error
        return {"took": 7, "hits": {"total": {"value": len(self._hits)}, "hits": self._hits}}


class FakeConnectionError(Exception):
    """Stand-in for an elasticsearch ConnectionError (matched by name + module)."""


FakeConnectionError.__module__ = "elastic_transport"


def _hit(product_id: str, score: float) -> dict[str, Any]:
    return {
        "_id": product_id,
        "_score": score,
        "_source": {
            "product_id": product_id,
            "title": f"Title {product_id}",
            "brand": "acme",
            "category": "widgets",
            "price": 19.99,
            "currency": "USD",
            "availability": "in_stock",
            "popularity_score": 42,
            "seller_id": "seller-1",
            "updated_at": "2026-01-01T00:00:00Z",
        },
    }


# --- product_search -------------------------------------------------------


def test_product_search_success_shape() -> None:
    client = FakeES(hits=[_hit("p1", 3.2), _hit("p2", 1.1)])

    result = product_search_impl("running shoes", "baseline_bm25", client=client, index="products-v1")

    assert "isError" not in result
    assert result["strategy"] == "baseline_bm25"
    assert result["query"] == "running shoes"
    assert result["total"] == 2
    assert result["count"] == 2
    assert result["took"] == 7
    first = result["products"][0]
    # Shaped product object, not a raw ES hit.
    assert first["productId"] == "p1"
    assert first["score"] == 3.2
    assert first["title"] == "Title p1"
    assert first["popularityScore"] == 42
    assert "_source" not in first
    # The chosen strategy's query body was sent to ES.
    assert client.search_calls and client.search_calls[0]["index"] == "products-v1"


def test_product_search_defaults_to_enriched_profile() -> None:
    client = FakeES(hits=[_hit("p1", 1.0)])

    result = product_search_impl("query", client=client, index="products-v1")

    assert result["strategy"] == "enriched_profile"


def test_product_search_invalid_strategy_is_validation_error() -> None:
    client = FakeES(hits=[])

    result = product_search_impl("query", "vector_only", client=client, index="products-v1")

    assert result["isError"] is True
    assert result["errorCategory"] == "validation"
    assert result["isRetryable"] is False
    assert "strategy" in result["message"]
    # No backend call should have been made for an invalid strategy.
    assert client.search_calls == []
    assert "Traceback" not in result["message"]


def test_product_search_empty_query_is_validation_error() -> None:
    client = FakeES(hits=[])

    result = product_search_impl("   ", "baseline_bm25", client=client, index="products-v1")

    assert result["isError"] is True
    assert result["errorCategory"] == "validation"
    assert result["isRetryable"] is False
    assert client.search_calls == []


def test_product_search_size_out_of_range_is_validation_error() -> None:
    client = FakeES(hits=[])

    result = product_search_impl("query", "baseline_bm25", size=999, client=client, index="products-v1")

    assert result["isError"] is True
    assert result["errorCategory"] == "validation"


def test_product_search_backend_unreachable_is_transient_error() -> None:
    client = FakeES(search_error=FakeConnectionError("connection refused"))

    result = product_search_impl("query", "baseline_bm25", client=client, index="products-v1")

    assert result["isError"] is True
    assert result["errorCategory"] == "transient"
    assert result["isRetryable"] is True
    assert "Traceback" not in result["message"]


# --- list_strategies ------------------------------------------------------


def test_list_strategies_returns_real_names() -> None:
    result = list_strategies_impl()

    assert "isError" not in result
    names = [item["name"] for item in result["strategies"]]
    assert names == list(STRATEGY_NAMES)
    assert set(names) == {"baseline_bm25", "boosted_bm25", "enriched_profile"}
    assert result["count"] == 3
    assert result["default"] == "enriched_profile"
    # Every strategy carries a non-empty one-line description.
    assert all(item["description"].strip() for item in result["strategies"])
