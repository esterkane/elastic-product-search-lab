"""Lexical, vector, and hybrid search helpers."""

from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from src.embeddings.embedder import Embedder
from src.evaluation.metrics import ndcg_at_k, precision_at_k, reciprocal_rank

StrategyName = Literal["baseline_lexical", "boosted_lexical", "hybrid_rrf"]


@dataclass(frozen=True)
class StrategyResult:
    strategy: StrategyName
    query: str
    ranked_product_ids: list[str]
    latency_ms: float


def baseline_lexical_query(query: str, size: int) -> dict[str, Any]:
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


def boosted_lexical_query(query: str, size: int) -> dict[str, Any]:
    return {
        "size": size,
        "query": {
            "function_score": {
                "query": baseline_lexical_query(query, size)["query"],
                "score_mode": "sum",
                "boost_mode": "sum",
                "functions": [
                    {"field_value_factor": {"field": "popularity_score", "factor": 0.02, "modifier": "sqrt", "missing": 0}},
                    {"gauss": {"updated_at": {"origin": "now", "scale": "30d", "offset": "7d", "decay": 0.5}}, "weight": 0.2},
                ],
            }
        },
        "sort": ["_score"],
    }


def extract_ids(response: Mapping[str, Any]) -> list[str]:
    return [str(hit["_id"]) for hit in response.get("hits", {}).get("hits", [])]


def lexical_search(client: Any, index_name: str, query: str, size: int, boosted: bool = False) -> list[str]:
    body = boosted_lexical_query(query, size) if boosted else baseline_lexical_query(query, size)
    return extract_ids(client.search(index=index_name, **body))


def knn_search(client: Any, index_name: str, query_vector: list[float], size: int, num_candidates: int = 100) -> list[str]:
    response = client.search(
        index=index_name,
        knn={"field": "embedding", "query_vector": query_vector, "k": size, "num_candidates": max(num_candidates, size)},
        size=size,
    )
    return extract_ids(response)


def elasticsearch_rrf_retriever_query(query: str, query_vector: list[float], size: int) -> dict[str, Any]:
    """Optional Elasticsearch retriever syntax for clusters that support RRF retrievers."""

    return {
        "size": size,
        "retriever": {
            "rrf": {
                "retrievers": [
                    {"standard": {"query": baseline_lexical_query(query, size)["query"]}},
                    {"knn": {"field": "embedding", "query_vector": query_vector, "k": size, "num_candidates": 100}},
                ],
                "rank_constant": 60,
                "rank_window_size": max(size, 50),
            }
        },
    }


def rrf_fuse(rankings: Sequence[Sequence[str]], size: int = 10, rank_constant: int = 60) -> list[str]:
    scores: dict[str, float] = {}
    first_seen: dict[str, int] = {}
    order = 0
    for ranking in rankings:
        for rank, product_id in enumerate(ranking, start=1):
            if product_id not in first_seen:
                first_seen[product_id] = order
                order += 1
            scores[product_id] = scores.get(product_id, 0.0) + 1.0 / (rank_constant + rank)
    return sorted(scores, key=lambda product_id: (-scores[product_id], first_seen[product_id]))[:size]


def hybrid_rrf_search(client: Any, index_name: str, query: str, embedder: Embedder, size: int) -> list[str]:
    query_vector = embedder.encode([query])[0]
    lexical_ids = lexical_search(client, index_name, query, size=size, boosted=True)
    try:
        vector_ids = knn_search(client, index_name, query_vector, size=size)
    except Exception as exc:  # noqa: BLE001 - vector path is optional and should degrade clearly.
        print(f"kNN search failed; falling back to lexical-only hybrid input: {exc}")
        vector_ids = []
    return rrf_fuse([lexical_ids, vector_ids], size=size)


def timed_strategy(strategy: StrategyName, query: str, search_fn: Any) -> StrategyResult:
    started = time.perf_counter()
    ranking = list(search_fn())
    latency_ms = (time.perf_counter() - started) * 1000
    return StrategyResult(strategy=strategy, query=query, ranked_product_ids=ranking, latency_ms=latency_ms)


def evaluate_rankings(
    rankings: Mapping[str, Mapping[str, Sequence[str]]],
    judgments: Mapping[str, Mapping[str, int]],
    k: int,
) -> dict[str, dict[str, float]]:
    totals: dict[str, dict[str, list[float]]] = {}
    for query, strategy_rankings in rankings.items():
        query_judgments = judgments.get(query, {})
        for strategy, ranking in strategy_rankings.items():
            bucket = totals.setdefault(strategy, {"precision_at_10": [], "mrr": [], "ndcg_at_10": []})
            bucket["precision_at_10"].append(precision_at_k(ranking, query_judgments, k))
            bucket["mrr"].append(reciprocal_rank(ranking, query_judgments))
            bucket["ndcg_at_10"].append(ndcg_at_k(ranking, query_judgments, k))
    return {
        strategy: {metric: sum(values) / len(values) if values else 0.0 for metric, values in metrics.items()}
        for strategy, metrics in totals.items()
    }