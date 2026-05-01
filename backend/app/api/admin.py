from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.app.retrieval.service import RECOMMENDATION_CATEGORIES


router = APIRouter(prefix="/api/v1", tags=["admin"])


class IngestRepoRequest(BaseModel):
    repo_url: str = Field(min_length=1)
    branch: str | None = None
    force: bool = False


class IngestRepoResponse(BaseModel):
    status: str
    repo_url: str
    branch: str | None = None
    message: str


class HealthResponse(BaseModel):
    status: str
    service: str


class MetricsResponse(BaseModel):
    service: str
    recommendation_categories: list[str]
    endpoints: dict[str, str]


@dataclass(frozen=True)
class LocalIngestionService:
    async def ingest_repo(self, request: IngestRepoRequest) -> IngestRepoResponse:
        return IngestRepoResponse(
            status="accepted",
            repo_url=request.repo_url,
            branch=request.branch,
            message="Repository ingestion accepted for local development.",
        )


def get_ingestion_service() -> LocalIngestionService:
    return LocalIngestionService()


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

