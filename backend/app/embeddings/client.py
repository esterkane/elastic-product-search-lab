from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class EmbeddingClient:
    endpoint_url: str
    model: str | None = None
    timeout: float = 30.0

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        payload: dict[str, Any] = {"inputs": texts}
        if self.model:
            payload["model"] = self.model

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.endpoint_url, json=payload)
            response.raise_for_status()
            data = response.json()

        return parse_embedding_response(data, expected_count=len(texts))


def parse_embedding_response(data: Any, expected_count: int) -> list[list[float]]:
    embeddings: Any
    if isinstance(data, dict):
        embeddings = data.get("embeddings", data.get("value", data.get("data")))
    else:
        embeddings = data

    if isinstance(embeddings, list) and embeddings and isinstance(embeddings[0], dict):
        embeddings = [item.get("embedding") for item in embeddings]

    if not isinstance(embeddings, list) or len(embeddings) != expected_count:
        raise ValueError(f"Embedding endpoint returned {len(embeddings) if isinstance(embeddings, list) else 0} vectors")

    vectors: list[list[float]] = []
    for embedding in embeddings:
        if not isinstance(embedding, list) or not all(isinstance(value, int | float) for value in embedding):
            raise ValueError("Embedding endpoint returned a malformed vector")
        vectors.append([float(value) for value in embedding])
    return vectors
