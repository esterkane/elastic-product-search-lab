from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urldefrag

import httpx
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.app.embeddings.client import EmbeddingClient
from backend.app.ingest.indexer import ACTIVE_REPOSITORY_SLUGS
from backend.app.vector.qdrant_client import SearchHit, VectorPayload, VectorRepository


RECOMMENDATION_CATEGORIES: tuple[str, ...] = (
    "relevance",
    "ingestion",
    "mapping",
    "performance",
    "resiliency",
)


@dataclass(frozen=True)
class RankedHit:
    id: str
    score: float
    metadata: VectorPayload
    source_url: str
    text: str = ""
    lexical_score: float = 0.0
    dense_score: float = 0.0
    fusion_score: float = 0.0
    rerank_score: float | None = None


class LexicalRepository(Protocol):
    async def search(self, query: str, limit: int, filters: dict | None = None) -> list[RankedHit]: ...


class PostgresFTSRepository:
    def __init__(self, engine: AsyncEngine, table_name: str = "document_chunks") -> None:
        self.engine = engine
        self.table_name = table_name

    async def search(self, query: str, limit: int, filters: dict | None = None) -> list[RankedHit]:
        where, params = postgres_filter_clause(filters or {})
        params.update({"query": query, "limit": limit})
        statement = text(
            f"""
            SELECT id, content, metadata, source_url,
                   ts_rank_cd(search_vector, websearch_to_tsquery('english', :query)) AS score
            FROM {self.table_name}
            WHERE search_vector @@ websearch_to_tsquery('english', :query)
            {where}
            ORDER BY score DESC
            LIMIT :limit
            """
        )
        try:
            async with self.engine.connect() as connection:
                result = await connection.execute(statement, params)
        except SQLAlchemyError as exc:
            if is_missing_relation(exc):
                return []
            raise

        hits: list[RankedHit] = []
        for row in result.mappings():
            metadata = dict(row["metadata"] or {})
            score = float(row["score"] or 0.0)
            hits.append(
                RankedHit(
                    id=str(row["id"]),
                    score=score,
                    lexical_score=score,
                    metadata=metadata,
                    source_url=str(row["source_url"]),
                    text=str(row["content"] or ""),
                )
            )
        return hits


class RerankerClient:
    def __init__(self, endpoint_url: str, model: str | None = None, timeout: float = 30.0) -> None:
        self.endpoint_url = endpoint_url
        self.model = model
        self.timeout = timeout

    async def rerank(self, query: str, hits: list[RankedHit]) -> list[RankedHit]:
        if not hits:
            return []

        payload: dict[str, object] = {
            "query": query,
            "texts": [hit.text or metadata_text(hit.metadata) for hit in hits],
        }
        if self.model:
            payload["model"] = self.model

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.endpoint_url, json=payload)
            response.raise_for_status()
            data = response.json()

        scores = parse_rerank_scores(data, expected_count=len(hits))
        reranked = [
            RankedHit(
                id=hit.id,
                score=float(score),
                metadata=hit.metadata,
                source_url=hit.source_url,
                text=hit.text,
                lexical_score=hit.lexical_score,
                dense_score=hit.dense_score,
                fusion_score=hit.fusion_score,
                rerank_score=float(score),
            )
            for hit, score in zip(hits, scores, strict=True)
        ]
        return sorted(reranked, key=lambda hit: (-hit.score, hit.id))


class RetrievalService:
    def __init__(
        self,
        lexical_repository: LexicalRepository,
        vector_repository: VectorRepository,
        embedding_client: EmbeddingClient,
        reranker_client: RerankerClient | None = None,
        default_repos: tuple[str, ...] = ACTIVE_REPOSITORY_SLUGS,
    ) -> None:
        self.lexical_repository = lexical_repository
        self.vector_repository = vector_repository
        self.embedding_client = embedding_client
        self.reranker_client = reranker_client
        self.default_repos = default_repos

    async def retrieve(self, query: str, limit: int = 10, filters: dict | None = None) -> dict[str, object]:
        effective_filters = active_repo_filters(filters, self.default_repos)
        lexical_hits = await self.lexical_repository.search(query, limit=50, filters=effective_filters)
        vectors = await self.embedding_client.embed([query])
        dense_hits = [
            vector_hit_to_ranked_hit(hit)
            for hit in await self.vector_repository.search(vectors[0], limit=50, filters=effective_filters)
        ]

        fused = reciprocal_rank_fusion(lexical_hits, dense_hits)[:20]
        ranked = await self.reranker_client.rerank(query, fused) if self.reranker_client else fused
        hits = with_final_ranks(diversify_hits(ranked, limit))
        return {
            "hits": hits,
            "recommendation_categories": list(RECOMMENDATION_CATEGORIES),
        }


def vector_hit_to_ranked_hit(hit: SearchHit) -> RankedHit:
    return RankedHit(
        id=hit.id,
        score=hit.score,
        dense_score=hit.score,
        metadata=hit.metadata,
        source_url=hit.source_url,
        text=metadata_text(hit.metadata),
    )


def reciprocal_rank_fusion(
    lexical_hits: list[RankedHit],
    dense_hits: list[RankedHit],
    k: int = 60,
) -> list[RankedHit]:
    by_id: dict[str, RankedHit] = {}
    scores: dict[str, float] = {}
    lexical_scores: dict[str, float] = {}
    dense_scores: dict[str, float] = {}

    for hits, channel in ((lexical_hits, "lexical"), (dense_hits, "dense")):
        for rank, hit in enumerate(hits, start=1):
            by_id.setdefault(hit.id, hit)
            scores[hit.id] = scores.get(hit.id, 0.0) + 1.0 / (k + rank)
            if channel == "lexical":
                lexical_scores[hit.id] = max(lexical_scores.get(hit.id, 0.0), hit.score)
            else:
                dense_scores[hit.id] = max(dense_scores.get(hit.id, 0.0), hit.score)

    fused: list[RankedHit] = []
    for hit_id, score in scores.items():
        hit = by_id[hit_id]
        fused.append(
            RankedHit(
                id=hit.id,
                score=score,
                metadata=hit.metadata,
                source_url=hit.source_url,
                text=hit.text,
                lexical_score=lexical_scores.get(hit.id, 0.0),
                dense_score=dense_scores.get(hit.id, 0.0),
                fusion_score=score,
            )
        )

    return sorted(fused, key=lambda hit: (-hit.score, hit.id))


def parse_rerank_scores(data: object, expected_count: int) -> list[float]:
    scores: object
    if isinstance(data, dict):
        scores = data.get("scores", data.get("results", data.get("data")))
    else:
        scores = data

    if isinstance(scores, list) and scores and isinstance(scores[0], dict):
        scores = [item.get("score") for item in scores]

    if not isinstance(scores, list) or len(scores) != expected_count:
        raise ValueError("Reranker endpoint returned an unexpected number of scores")
    if not all(isinstance(score, int | float) for score in scores):
        raise ValueError("Reranker endpoint returned a malformed score")
    return [float(score) for score in scores]


def metadata_text(metadata: VectorPayload) -> str:
    parts = [
        metadata.get("title"),
        metadata.get("heading_path"),
        metadata.get("content_type"),
    ]
    return " ".join(str(part) for part in parts if part)


def postgres_filter_clause(filters: dict) -> tuple[str, dict[str, object]]:
    if not filters:
        return "", {}

    clauses: list[str] = []
    params: dict[str, object] = {}
    for index, (key, value) in enumerate(sorted(filters.items())):
        if value is None:
            continue
        key_param = f"filter_key_{index}"
        params[key_param] = str(key)
        if isinstance(value, list | tuple | set):
            value_params: list[str] = []
            for value_index, item in enumerate(value):
                value_param = f"filter_value_{index}_{value_index}"
                value_params.append(f":{value_param}")
                params[value_param] = str(item)
            if not value_params:
                continue
            clauses.append(f"AND (metadata ->> :{key_param}) IN ({', '.join(value_params)})")
        else:
            value_param = f"filter_value_{index}"
            clauses.append(f"AND (metadata ->> :{key_param}) = :{value_param}")
            params[value_param] = str(value)
    return ("\n".join(clauses), params)


def active_repo_filters(filters: dict | None, default_repos: tuple[str, ...]) -> dict[str, object] | None:
    merged: dict[str, object] = dict(filters or {})
    if default_repos and not merged.get("repo"):
        merged["repo"] = list(default_repos)
    return merged or None


def diversify_hits(hits: list[RankedHit], limit: int) -> list[RankedHit]:
    selected: list[RankedHit] = []
    seen_pages: set[str] = set()
    seen_titles: set[str] = set()

    for hit in hits:
        page_key = canonical_source_key(hit.source_url)
        title_key = str(hit.metadata.get("title") or hit.metadata.get("heading_path") or "").strip().lower()
        if page_key and page_key in seen_pages:
            continue
        if title_key and title_key in seen_titles:
            continue
        selected.append(hit)
        if page_key:
            seen_pages.add(page_key)
        if title_key:
            seen_titles.add(title_key)
        if len(selected) >= limit:
            return selected

    for hit in hits:
        if hit.id not in {selected_hit.id for selected_hit in selected}:
            selected.append(hit)
        if len(selected) >= limit:
            break
    return selected


def canonical_source_key(source_url: str) -> str:
    return urldefrag(source_url)[0].rstrip("/")


def with_final_ranks(hits: list[RankedHit]) -> list[RankedHit]:
    ranked: list[RankedHit] = []
    for index, hit in enumerate(hits, start=1):
        metadata = dict(hit.metadata)
        metadata["final_rank"] = index
        ranked.append(
            RankedHit(
                id=hit.id,
                score=hit.score,
                metadata=metadata,
                source_url=hit.source_url,
                text=hit.text,
                lexical_score=hit.lexical_score,
                dense_score=hit.dense_score,
                fusion_score=hit.fusion_score,
                rerank_score=hit.rerank_score,
            )
        )
    return ranked


def is_missing_relation(exc: SQLAlchemyError) -> bool:
    message = str(exc).lower()
    return "undefinedtable" in message or "does not exist" in message or "undefined table" in message
