from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx


VectorPayload = dict[str, str | int | float | bool | None]


@dataclass(frozen=True)
class VectorPoint:
    id: str
    vector: list[float]
    payload: VectorPayload
    source_url: str


@dataclass(frozen=True)
class SearchHit:
    id: str
    score: float
    metadata: VectorPayload
    source_url: str


class VectorRepository(Protocol):
    async def upsert(self, points: list[VectorPoint]) -> None: ...

    async def search(self, vector: list[float], limit: int, filters: dict | None = None) -> list[SearchHit]: ...


class QdrantVectorRepository:
    def __init__(self, base_url: str, collection: str, api_key: str | None = None, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.collection = collection
        self.timeout = timeout
        self.headers = {"api-key": api_key} if api_key else {}

    async def upsert(self, points: list[VectorPoint]) -> None:
        if not points:
            return

        payload = {
            "points": [
                {
                    "id": point.id,
                    "vector": point.vector,
                    "payload": {**point.payload, "source_url": point.source_url},
                }
                for point in points
            ]
        }
        url = f"{self.base_url}/collections/{self.collection}/points?wait=true"
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            response = await client.put(url, json=payload)
            response.raise_for_status()

    async def search(self, vector: list[float], limit: int, filters: dict | None = None) -> list[SearchHit]:
        payload: dict[str, object] = {"vector": vector, "limit": limit, "with_payload": True}
        if filters:
            payload["filter"] = qdrant_filter(filters)

        url = f"{self.base_url}/collections/{self.collection}/points/search"
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        return [qdrant_hit_to_search_hit(hit) for hit in data.get("result", [])]


def qdrant_filter(filters: dict) -> dict:
    return {
        "must": [
            {"key": key, "match": {"value": value}}
            for key, value in sorted(filters.items())
            if value is not None
        ]
    }


def qdrant_hit_to_search_hit(hit: dict) -> SearchHit:
    payload = dict(hit.get("payload") or {})
    source_url = str(payload.get("source_url") or "")
    return SearchHit(
        id=str(hit.get("id")),
        score=float(hit.get("score", 0.0)),
        metadata=payload,
        source_url=source_url,
    )


def vector_payload(
    *,
    repo: str,
    path: str,
    title: str | None,
    heading_path: str | None,
    content_type: str,
    license_family: str,
    source_url: str,
) -> VectorPayload:
    return {
        "repo": repo,
        "path": path,
        "title": title,
        "heading_path": heading_path,
        "content_type": content_type,
        "license_family": license_family,
        "source_url": source_url,
    }

