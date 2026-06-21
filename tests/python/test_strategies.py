"""Unit tests for the shared strategy registry and search shaping."""

from __future__ import annotations

from typing import Any

import pytest

from src.search.strategies import (
    DEFAULT_STRATEGY,
    STRATEGY_NAMES,
    build_strategy_query,
    is_strategy,
    normalize_product_hit,
    search_products,
)


class FakeES:
    def __init__(self, response: dict[str, Any]) -> None:
        self._response = response
        self.calls: list[dict[str, Any]] = []

    def search(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return self._response


def test_strategy_names_are_the_three_comparable_strategies() -> None:
    assert STRATEGY_NAMES == ("baseline_bm25", "boosted_bm25", "enriched_profile")
    assert DEFAULT_STRATEGY == "enriched_profile"


@pytest.mark.parametrize("strategy", STRATEGY_NAMES)
def test_build_strategy_query_returns_sized_body(strategy: str) -> None:
    body = build_strategy_query(strategy, "wireless earbuds", 5)
    assert body["size"] == 5
    assert "query" in body


def test_build_strategy_query_rejects_unknown_strategy() -> None:
    assert not is_strategy("hybrid_rrf")
    with pytest.raises(ValueError):
        build_strategy_query("hybrid_rrf", "q", 5)


def test_normalize_product_hit_shapes_source() -> None:
    hit = {"_id": "x", "_score": 2.5, "_source": {"product_id": "p9", "title": "Hat", "price": 5}}
    shaped = normalize_product_hit(hit)
    assert shaped["productId"] == "p9"
    assert shaped["title"] == "Hat"
    assert shaped["price"] == 5.0
    assert shaped["score"] == 2.5
    assert "_source" not in shaped


def test_search_products_returns_shaped_response() -> None:
    client = FakeES(
        {
            "took": 4,
            "hits": {"total": {"value": 1}, "hits": [{"_id": "p1", "_score": 1.0, "_source": {"product_id": "p1"}}]},
        }
    )
    result = search_products(client, "products-v1", "shoes", "baseline_bm25", 10)
    assert result["strategy"] == "baseline_bm25"
    assert result["total"] == 1
    assert result["count"] == 1
    assert result["products"][0]["productId"] == "p1"
    assert client.calls[0]["index"] == "products-v1"
