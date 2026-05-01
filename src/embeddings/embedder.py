"""Optional local embedding providers for product semantic search."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Iterable
from typing import Any, Protocol

EMBEDDING_DIMS = 384
DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class Embedder(Protocol):
    dims: int

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Encode text into dense vectors."""


class SentenceTransformersEmbedder:
    """Sentence Transformers embedder using a compact 384-dimensional model."""

    dims = EMBEDDING_DIMS

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME) -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is not installed. Install optional dependencies with: "
                'python -m pip install -e ".[vector]"'
            ) from exc

        self.model = SentenceTransformer(model_name)

    def encode(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(texts, normalize_embeddings=True)
        return [list(map(float, vector)) for vector in vectors]


class DeterministicHashEmbedder:
    """Small deterministic fallback embedder for tests and credential-free demos."""

    dims = EMBEDDING_DIMS

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [self._encode_one(text) for text in texts]

    def _encode_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dims
        tokens = [token for token in text.lower().replace("-", " ").split() if token]
        for token in tokens or [text.lower()]:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for offset in range(0, len(digest), 2):
                index = int.from_bytes(digest[offset : offset + 2], "big") % self.dims
                sign = 1.0 if digest[offset] % 2 == 0 else -1.0
                vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


def get_embedder(provider: str = "auto", model_name: str = DEFAULT_MODEL_NAME) -> Embedder:
    if provider == "hash":
        return DeterministicHashEmbedder()
    if provider == "sentence-transformers":
        return SentenceTransformersEmbedder(model_name)
    if provider != "auto":
        raise ValueError("provider must be one of: auto, sentence-transformers, hash")

    try:
        return SentenceTransformersEmbedder(model_name)
    except RuntimeError:
        print("sentence-transformers unavailable; using deterministic hash embeddings for local demo.")
        return DeterministicHashEmbedder()


def build_embedding_text(product: dict[str, Any]) -> str:
    return " ".join(
        str(part)
        for part in [
            product.get("title", ""),
            product.get("brand", ""),
            product.get("category", ""),
            product.get("description", ""),
        ]
        if part
    )


def batched(items: list[Any], batch_size: int) -> Iterable[list[Any]]:
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    for start in range(0, len(items), batch_size):
        yield items[start : start + batch_size]