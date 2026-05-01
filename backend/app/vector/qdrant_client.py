from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import NAMESPACE_URL, uuid5

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

    async def ensure_collection(self, vector_size: int) -> None:
        collection_url = f"{self.base_url}/collections/{self.collection}"
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            response = await client.get(collection_url)
            if response.status_code == 200:
                return
            if response.status_code != 404:
                response.raise_for_status()

            create_response = await client.put(
                collection_url,
                json={"vectors": {"size": vector_size, "distance": "Cosine"}},
            )
            create_response.raise_for_status()

    async def upsert(self, points: list[VectorPoint]) -> None:
        if not points:
            return

        payload = {
            "points": [
                {
                    "id": qdrant_point_id(point.id),
                    "vector": point.vector,
                    "payload": {**point.payload, "chunk_id": point.id, "source_url": point.source_url},
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
            if response.status_code == 404:
                return []
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
        id=str(payload.get("chunk_id") or hit.get("id")),
        score=float(hit.get("score", 0.0)),
        metadata=payload,
        source_url=source_url,
    )


def qdrant_point_id(chunk_id: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"elastic-repo-inventory:{chunk_id}"))


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
