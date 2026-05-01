"""Optional reranking interfaces for search experiments.

The local placeholder reranker in this module is deterministic and useful for
workflow tests. It is not a machine-learning reranker and should not be treated
as a production semantic model.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from typing import Any

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class SearchResult:
    product_id: str
    score: float = 0.0
    title: str = ""
    brand: str = ""
    category: str = ""
    description: str = ""
    catalog_text: str = ""
    source: dict[str, Any] | None = None

    @property
    def text(self) -> str:
        return " ".join(part for part in [self.title, self.brand, self.category, self.description, self.catalog_text] if part)


class Reranker(ABC):
    """Interface for reranking a first-stage candidate set."""

    @abstractmethod
    def rerank(self, query: str, candidates: list[SearchResult]) -> list[SearchResult]:
        """Return the same candidate IDs in a new order."""


class PlaceholderTextSimilarityReranker(Reranker):
    """Deterministic text-overlap reranker for local demos and tests.

    This is a placeholder. It does not use cross-encoders, LLMs, learned ranking,
    or Elastic semantic reranking. Its purpose is to demonstrate where reranking
    sits in the retrieval pipeline and how to measure quality/latency tradeoffs.
    """

    def rerank(self, query: str, candidates: list[SearchResult]) -> list[SearchResult]:
        query_tokens = tokenize(query)
        scored: list[tuple[float, int, SearchResult]] = []
        for position, candidate in enumerate(candidates):
            similarity = deterministic_text_similarity(query_tokens, tokenize(candidate.text))
            # Keep a small contribution from first-stage score so exact ties do
            # not discard useful retrieval signal.
            rerank_score = similarity + (candidate.score * 0.001)
            scored.append((rerank_score, position, replace(candidate, score=rerank_score)))
        return [candidate for _, _, candidate in sorted(scored, key=lambda item: (-item[0], item[1]))]


def tokenize(text: str) -> set[str]:
    return set(TOKEN_PATTERN.findall(text.lower()))


def deterministic_text_similarity(query_tokens: set[str], document_tokens: set[str]) -> float:
    if not query_tokens or not document_tokens:
        return 0.0
    overlap = len(query_tokens & document_tokens)
    return overlap / len(query_tokens | document_tokens)


def rerank_window(query: str, candidates: list[SearchResult], reranker: Reranker, window_size: int) -> list[SearchResult]:
    if window_size < 1:
        raise ValueError("window_size must be positive")
    reranked = reranker.rerank(query, candidates[:window_size])
    return reranked + candidates[window_size:]


def metric_delta(before: dict[str, float], after: dict[str, float]) -> dict[str, float]:
    return {metric: after.get(metric, 0.0) - before.get(metric, 0.0) for metric in sorted(set(before) | set(after))}
