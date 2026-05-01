from __future__ import annotations

import math
from collections.abc import Sequence


def ndcg_at_k(ranked_ids: Sequence[str], relevance: dict[str, int | float], k: int = 10) -> float:
    dcg = 0.0
    for index, item_id in enumerate(ranked_ids[:k], start=1):
        gain = float(relevance.get(item_id, 0.0))
        dcg += (2**gain - 1) / math.log2(index + 1)

    ideal_gains = sorted((float(value) for value in relevance.values()), reverse=True)[:k]
    idcg = sum((2**gain - 1) / math.log2(index + 1) for index, gain in enumerate(ideal_gains, start=1))
    return dcg / idcg if idcg else 0.0


def mrr_at_k(ranked_ids: Sequence[str], relevant_ids: set[str], k: int = 10) -> float:
    for index, item_id in enumerate(ranked_ids[:k], start=1):
        if item_id in relevant_ids:
            return 1.0 / index
    return 0.0


def recall_at_k(ranked_ids: Sequence[str], relevant_ids: set[str], k: int = 20) -> float:
    if not relevant_ids:
        return 0.0
    retrieved = set(ranked_ids[:k])
    return len(retrieved & relevant_ids) / len(relevant_ids)

