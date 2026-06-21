"""Single source of truth for the three comparable product-search strategies.

The lab compares three BM25-family strategies side by side:

- ``baseline_bm25``     — plain multi-field BM25 over title/brand/category/etc.
- ``boosted_bm25``      — BM25 plus a popularity / freshness ``function_score``.
- ``enriched_profile``  — BM25 over the deterministic ingestion-time
  ``search_profile`` field (plus title/category/brand context).

These query builders previously lived inline in ``scripts/evaluate_relevance.py``
and ``scripts/benchmark_search.py``. They are consolidated here so the API
route, the evaluation/benchmark CLIs, *and* the MCP tools all share one
implementation and stay comparable (an invariant in CLAUDE.md). The scripts
re-export the builders from this module for backwards compatibility.

Nothing in this module performs I/O beyond the single ``client.search`` call in
:func:`search_products`; it is import-safe and side-effect free, so it can be
unit-tested with a fake Elasticsearch client.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

StrategyName = Literal["baseline_bm25", "boosted_bm25", "enriched_profile"]


@dataclass(frozen=True)
class StrategyInfo:
    """A strategy's stable name plus a one-line human description."""

    name: StrategyName
    description: str


# Ordered registry — the canonical list of executable strategy names and the
# one-line descriptions surfaced by ``list_strategies``.
STRATEGY_INFOS: tuple[StrategyInfo, ...] = (
    StrategyInfo(
        "baseline_bm25",
        "Plain multi-field BM25 over title/brand/category/description/catalog_text "
        "with AND semantics. The relevance baseline.",
    ),
    StrategyInfo(
        "boosted_bm25",
        "BM25 plus a function_score that rewards popularity and recency; uses OR "
        "semantics with fuzziness for higher recall.",
    ),
    StrategyInfo(
        "enriched_profile",
        "BM25 over the deterministic ingestion-time search_profile field plus "
        "title/category/brand context; readable and reproducible.",
    ),
)

# Tuple of names, matching the historical ``STRATEGIES`` constant order.
STRATEGY_NAMES: tuple[StrategyName, ...] = tuple(info.name for info in STRATEGY_INFOS)

DEFAULT_STRATEGY: StrategyName = "enriched_profile"

# Upper bound on requested result size, matching the HTTP /search route schema
# (apps/api/src/routes/search.ts: size maximum 50).
MAX_SIZE = 50


def baseline_bm25_query(query: str, size: int) -> dict[str, Any]:
    """Plain multi-field BM25 with AND semantics (the relevance baseline)."""

    return {
        "size": size,
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["title^4", "brand^2", "category^1.5", "description^0.8", "catalog_text^0.5"],
                "type": "best_fields",
                "operator": "and",
            }
        },
        "sort": ["_score"],
    }


def boosted_bm25_query(query: str, size: int) -> dict[str, Any]:
    """More forgiving BM25 variant with popularity + freshness boosts."""

    return {
        "size": size,
        "query": {
            "function_score": {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["title^4", "brand^2", "category^1.5", "description", "catalog_text^0.8"],
                        "type": "best_fields",
                        "operator": "or",
                        "minimum_should_match": "2<75%",
                        "fuzziness": "AUTO",
                    }
                },
                "score_mode": "sum",
                "boost_mode": "sum",
                "functions": [
                    {"field_value_factor": {"field": "popularity_score", "factor": 0.01, "modifier": "sqrt", "missing": 0}},
                    {"gauss": {"updated_at": {"origin": "now", "scale": "30d", "offset": "7d", "decay": 0.5}}, "weight": 0.1},
                ],
            }
        },
        "sort": ["_score"],
    }


def enriched_profile_query(query: str, size: int) -> dict[str, Any]:
    """BM25 over the ingestion-time enriched ``search_profile`` field."""

    return {
        "size": size,
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["search_profile^3", "title^2", "category^1.5", "brand", "description^0.5"],
                "type": "best_fields",
                "operator": "or",
                "minimum_should_match": "2<70%",
                "fuzziness": "AUTO",
            }
        },
        "sort": ["_score"],
    }


_QUERY_BUILDERS = {
    "baseline_bm25": baseline_bm25_query,
    "boosted_bm25": boosted_bm25_query,
    "enriched_profile": enriched_profile_query,
}


def is_strategy(strategy: str) -> bool:
    """True if ``strategy`` is one of the executable strategy names."""

    return strategy in _QUERY_BUILDERS


def build_strategy_query(strategy: str, query: str, size: int) -> dict[str, Any]:
    """Return the Elasticsearch request body for ``strategy``.

    Raises :class:`ValueError` for an unknown strategy so callers can map it to
    their own error contract.
    """

    builder = _QUERY_BUILDERS.get(strategy)
    if builder is None:
        raise ValueError(f"Unsupported strategy: {strategy!r}. Expected one of {STRATEGY_NAMES}.")
    return builder(query, size)


def normalize_product_hit(hit: Mapping[str, Any]) -> dict[str, Any]:
    """Shape a raw Elasticsearch hit into the lab's product result object.

    Mirrors ``apps/api/src/search/normalize.ts`` so the MCP tools return the
    same shaped product objects the HTTP API returns — never a raw ES hit.
    """

    source: Mapping[str, Any] = hit.get("_source") or {}
    return {
        "productId": str(source.get("product_id", hit.get("_id", ""))),
        "title": str(source.get("title", "")),
        "description": str(source.get("description", "")),
        "brand": str(source.get("brand", "")),
        "category": str(source.get("category", "")),
        "attributes": source.get("attributes") or {},
        "price": float(source.get("price", 0) or 0),
        "currency": str(source.get("currency", "")),
        "availability": str(source.get("availability", "")),
        "popularityScore": float(source.get("popularity_score", 0) or 0),
        "sellerId": str(source.get("seller_id", "")),
        "updatedAt": str(source.get("updated_at", "")),
        "score": hit.get("_score"),
    }


def _total_hits_value(total: Any) -> int:
    if isinstance(total, (int, float)):
        return int(total)
    if isinstance(total, Mapping) and "value" in total:
        return int(total["value"])
    return 0


def search_products(client: Any, index_name: str, query: str, strategy: str, size: int) -> dict[str, Any]:
    """Execute ``strategy`` against ``index_name`` and return shaped results.

    Returns the same shape as the HTTP ``/search`` response::

        {"strategy", "query", "took", "total", "count", "products": [...]}

    where each product is produced by :func:`normalize_product_hit`. ``client``
    only needs a ``.search(index=..., **body)`` method, so a fake can stand in.
    """

    body = build_strategy_query(strategy, query, size)
    response = client.search(index=index_name, **body)
    hits = (response.get("hits") or {}).get("hits") or []
    products = [normalize_product_hit(hit) for hit in hits]
    return {
        "strategy": strategy,
        "query": query,
        "took": int(response.get("took", 0) or 0),
        "total": _total_hits_value((response.get("hits") or {}).get("total")),
        "count": len(products),
        "products": products,
    }
