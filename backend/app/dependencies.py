from __future__ import annotations

import os
from functools import lru_cache

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from backend.app.embeddings.client import EmbeddingClient
from backend.app.retrieval.service import PostgresFTSRepository, RerankerClient, RetrievalService, RetryPolicy
from backend.app.vector.qdrant_client import QdrantVectorRepository


@lru_cache(maxsize=1)
def get_async_engine() -> AsyncEngine:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise service_not_configured("DATABASE_URL is not set.")
    return create_async_engine(database_url, pool_pre_ping=True)


@lru_cache(maxsize=1)
def build_retrieval_service() -> RetrievalService:
    qdrant_url = os.getenv("QDRANT_URL")
    tei_embed_url = os.getenv("TEI_EMBED_URL")
    if not qdrant_url or not tei_embed_url:
        missing = [name for name, value in {"QDRANT_URL": qdrant_url, "TEI_EMBED_URL": tei_embed_url}.items() if not value]
        raise service_not_configured(f"Missing required settings: {', '.join(missing)}.")

    rerank_url = os.getenv("TEI_RERANK_URL")
    return RetrievalService(
        lexical_repository=PostgresFTSRepository(get_async_engine()),
        vector_repository=QdrantVectorRepository(
            base_url=qdrant_url,
            collection=os.getenv("QDRANT_COLLECTION", "repo-docs"),
            api_key=os.getenv("QDRANT_API_KEY"),
        ),
        embedding_client=EmbeddingClient(tei_embed_url, model=os.getenv("TEI_EMBED_MODEL")),
        reranker_client=RerankerClient(rerank_url, model=os.getenv("TEI_RERANK_MODEL")) if rerank_url else None,
        retry_policy=RetryPolicy(
            attempts=int(os.getenv("RETRIEVAL_RETRY_ATTEMPTS", "2")),
            backoff_seconds=float(os.getenv("RETRIEVAL_RETRY_BACKOFF_SECONDS", "0.2")),
        ),
    )


async def get_retrieval_service() -> RetrievalService:
    return build_retrieval_service()


def service_not_configured(message: str) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={
            "code": "retrieval_not_configured",
            "message": f"Retrieval service is not configured for this environment. {message}",
        },
    )
