from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.retrieval.service import RankedHit, RetrievalService


router = APIRouter(prefix="/api/v1", tags=["search"])


class SearchFilters(BaseModel):
    repo: str | None = None
    content_type: str | None = None

    def as_dict(self) -> dict[str, str]:
        return {
            key: value
            for key, value in {
                "repo": self.repo,
                "content_type": self.content_type,
            }.items()
            if value
        }


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=10, ge=1, le=50)
    filters: SearchFilters | None = None


class SourceAttribution(BaseModel):
    title: str
    url: str


class SearchHitResponse(BaseModel):
    id: str
    score: float
    title: str | None = None
    repo: str | None = None
    path: str | None = None
    heading_path: str | None = None
    content_type: str | None = None
    license_family: str | None = None
    source_url: str


class SearchResponse(BaseModel):
    hits: list[SearchHitResponse]
    recommendation_categories: list[str]


class AnswerRequest(SearchRequest):
    pass


class AnswerResponse(BaseModel):
    answer: str
    sources: list[SourceAttribution]


async def get_retrieval_service() -> RetrievalService:
    raise HTTPException(
        status_code=503,
        detail={
            "code": "retrieval_not_configured",
            "message": "Retrieval service is not configured for this environment.",
        },
    )


RetrievalDependency = Annotated[RetrievalService, Depends(get_retrieval_service)]


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest, retrieval_service: RetrievalDependency) -> SearchResponse:
    result = await retrieval_service.retrieve(
        request.query,
        limit=request.limit,
        filters=request.filters.as_dict() if request.filters else None,
    )
    return SearchResponse(
        hits=[hit_response(hit) for hit in result.get("hits", [])],
        recommendation_categories=[str(category) for category in result.get("recommendation_categories", [])],
    )


@router.post("/answer", response_model=AnswerResponse)
async def answer(request: AnswerRequest, retrieval_service: RetrievalDependency) -> AnswerResponse:
    result = await retrieval_service.retrieve(
        request.query,
        limit=request.limit,
        filters=request.filters.as_dict() if request.filters else None,
    )
    hits = [hit for hit in result.get("hits", []) if isinstance(hit, RankedHit)]
    sources = source_attributions(hits)
    return AnswerResponse(answer=synthesize_answer(request.query, hits), sources=sources)


def hit_response(hit: object) -> SearchHitResponse:
    if not isinstance(hit, RankedHit):
        raise TypeError("retrieval result contains an unsupported hit")

    return SearchHitResponse(
        id=hit.id,
        score=hit.score,
        title=metadata_value(hit, "title"),
        repo=metadata_value(hit, "repo"),
        path=metadata_value(hit, "path"),
        heading_path=metadata_value(hit, "heading_path"),
        content_type=metadata_value(hit, "content_type"),
        license_family=metadata_value(hit, "license_family"),
        source_url=hit.source_url,
    )


def metadata_value(hit: RankedHit, key: str) -> str | None:
    value = hit.metadata.get(key)
    return str(value) if value is not None else None


def source_attributions(hits: list[RankedHit]) -> list[SourceAttribution]:
    sources: list[SourceAttribution] = []
    seen: set[str] = set()
    for hit in hits:
        if not hit.source_url or hit.source_url in seen:
            continue
        seen.add(hit.source_url)
        sources.append(
            SourceAttribution(
                title=metadata_value(hit, "title") or metadata_value(hit, "heading_path") or hit.id,
                url=hit.source_url,
            )
        )
    return sources


def synthesize_answer(query: str, hits: list[RankedHit]) -> str:
    if not hits:
        return f"No grounded sources were found for '{query}'."

    top = hits[0]
    title = metadata_value(top, "title") or metadata_value(top, "heading_path") or "the strongest source"
    if len(hits) > 1:
        return f"The strongest improvement is to use {title} as the primary source and validate it against the other retrieved evidence."
    return f"The strongest improvement is to use {title} as the primary grounded source."

