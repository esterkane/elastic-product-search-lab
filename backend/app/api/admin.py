from __future__ import annotations

import asyncio
import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.dependencies import get_async_engine, service_not_configured
from backend.app.embeddings.client import EmbeddingClient
from backend.app.ingest.indexer import RepositoryIndexer
from backend.app.retrieval.service import RECOMMENDATION_CATEGORIES
from backend.app.vector.qdrant_client import QdrantVectorRepository


router = APIRouter(prefix="/api/v1", tags=["admin"])


class IngestRepoRequest(BaseModel):
    repo_url: str | None = None
    repo: str | None = None
    branch: str | None = None
    force: bool = False
    update_sources: bool = True
    max_files: int | None = Field(default=None, gt=0)


class IngestRepoResponse(BaseModel):
    status: str
    repo_url: str
    branch: str | None = None
    message: str
    repos_scanned: int = 0
    documents_scanned: int = 0
    chunks_indexed: int = 0
    new_chunks: int = 0
    updated_chunks: int = 0
    unchanged_chunks: int = 0
    errors: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    service: str


class MetricsResponse(BaseModel):
    service: str
    recommendation_categories: list[str]
    endpoints: dict[str, str]


class LocalIngestionService:
    def __init__(self, indexer: RepositoryIndexer) -> None:
        self.indexer = indexer
        self._lock = asyncio.Lock()

    async def ingest_repo(self, request: IngestRepoRequest) -> IngestRepoResponse:
        if self._lock.locked():
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "ingestion_in_progress",
                    "message": "A repository ingestion job is already running. Wait for it to finish before starting another.",
                },
            )
        async with self._lock:
            result = await self.indexer.index(
                repo_url=request.repo_url,
                repo_slug=request.repo,
                branch=request.branch,
                force=request.force,
                update_sources=request.update_sources,
                max_files=request.max_files,
            )
        return IngestRepoResponse(
            status=result.status,
            repo_url=result.repo_url,
            branch=result.branch,
            message=result.message,
            repos_scanned=result.repos_scanned,
            documents_scanned=result.documents_scanned,
            chunks_indexed=result.chunks_indexed,
            new_chunks=result.new_chunks,
            updated_chunks=result.updated_chunks,
            unchanged_chunks=result.unchanged_chunks,
            errors=result.errors,
        )


@lru_cache(maxsize=1)
def get_ingestion_service() -> LocalIngestionService:
    qdrant_url = os.getenv("QDRANT_URL")
    tei_embed_url = os.getenv("TEI_EMBED_URL")
    if not qdrant_url or not tei_embed_url:
        missing = [name for name, value in {"QDRANT_URL": qdrant_url, "TEI_EMBED_URL": tei_embed_url}.items() if not value]
        raise service_not_configured(f"Missing required settings: {', '.join(missing)}.")

    indexer = RepositoryIndexer(
        sources_dir=Path(os.getenv("SOURCES_DIR", "sources")),
        engine=get_async_engine(),
        embedding_client=EmbeddingClient(tei_embed_url, model=os.getenv("TEI_EMBED_MODEL")),
        vector_repository=QdrantVectorRepository(
            base_url=qdrant_url,
            collection=os.getenv("QDRANT_COLLECTION", "repo-docs"),
            api_key=os.getenv("QDRANT_API_KEY"),
        ),
        embedding_batch_size=int(os.getenv("INGEST_EMBED_BATCH_SIZE", "8")),
        upsert_batch_size=int(os.getenv("INGEST_UPSERT_BATCH_SIZE", "64")),
    )
    return LocalIngestionService(indexer)


IngestionDependency = Annotated[LocalIngestionService, Depends(get_ingestion_service)]


@router.post("/ingest/repo", response_model=IngestRepoResponse)
async def ingest_repo(request: IngestRepoRequest, ingestion_service: IngestionDependency) -> IngestRepoResponse:
    return await ingestion_service.ingest_repo(request)


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="elastic-repo-inventory")


@router.get("/metrics", response_model=MetricsResponse)
async def metrics() -> MetricsResponse:
    return MetricsResponse(
        service="elastic-repo-inventory",
        recommendation_categories=list(RECOMMENDATION_CATEGORIES),
        endpoints={
            "ingest_repo": "POST /api/v1/ingest/repo",
            "search": "POST /api/v1/search",
            "analyze": "POST /api/v1/analyze",
            "answer": "POST /api/v1/answer",
        },
    )
