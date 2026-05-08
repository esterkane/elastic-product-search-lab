from __future__ import annotations

import math
import statistics
from collections.abc import Sequence


def ndcg_at_k(ranked_ids: Sequence[str], relevance: dict[str, int | float], k: int = 10) -> float:
    dcg = 0.0
    for index, doc_id in enumerate(ranked_ids[:k], start=1):
        gain = float(relevance.get(doc_id, 0.0))
        dcg += (2**gain - 1) / math.log2(index + 1)
    ideal = sorted((float(value) for value in relevance.values()), reverse=True)[:k]
    idcg = sum((2**gain - 1) / math.log2(index + 1) for index, gain in enumerate(ideal, start=1))
    return dcg / idcg if idcg else 0.0


def precision_at_k(ranked_ids: Sequence[str], relevant_ids: set[str], k: int = 5) -> float:
    return len(set(ranked_ids[:k]) & relevant_ids) / k if k > 0 else 0.0


def recall_at_k(ranked_ids: Sequence[str], relevant_ids: set[str], k: int = 10) -> float:
    if not relevant_ids:
        return 0.0
    return len(set(ranked_ids[:k]) & relevant_ids) / len(relevant_ids)


def mrr_at_k(ranked_ids: Sequence[str], relevant_ids: set[str], k: int = 10) -> float:
    for index, doc_id in enumerate(ranked_ids[:k], start=1):
        if doc_id in relevant_ids:
            return 1.0 / index
    return 0.0


def percentile(values: Sequence[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * percentile_value / 100
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[int(rank)]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)


def mean(values: Sequence[float]) -> float:
    return statistics.fmean(values) if values else 0.0
