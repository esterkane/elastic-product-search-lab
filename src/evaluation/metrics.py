"""Offline relevance metrics for ranked product search results."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence


def precision_at_k(ranked_product_ids: Sequence[str], judgments: Mapping[str, int], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    if not ranked_product_ids:
        return 0.0

    top_k = ranked_product_ids[:k]
    relevant = sum(1 for product_id in top_k if judgments.get(product_id, 0) > 0)
    return relevant / min(k, len(top_k))


def reciprocal_rank(ranked_product_ids: Sequence[str], judgments: Mapping[str, int]) -> float:
    for rank, product_id in enumerate(ranked_product_ids, start=1):
        if judgments.get(product_id, 0) > 0:
            return 1.0 / rank
    return 0.0


def dcg_at_k(relevances: Sequence[int], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")

    score = 0.0
    for index, relevance in enumerate(relevances[:k], start=1):
        gain = (2**relevance) - 1
        discount = math.log2(index + 1)
        score += gain / discount
    return score


def ndcg_at_k(ranked_product_ids: Sequence[str], judgments: Mapping[str, int], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")

    actual_relevances = [judgments.get(product_id, 0) for product_id in ranked_product_ids[:k]]
    ideal_relevances = sorted(judgments.values(), reverse=True)[:k]
    ideal = dcg_at_k(ideal_relevances, k)
    if ideal == 0:
        return 0.0
    return dcg_at_k(actual_relevances, k) / ideal