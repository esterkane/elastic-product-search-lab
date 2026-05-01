from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.app.api.search import SearchBoosts, SearchFilters, SourceAttribution, WarningResponse, get_retrieval_service, warning_responses
from backend.app.recommend.service import RecommendationEngine
from backend.app.retrieval.service import RankedHit, RetrievalService


router = APIRouter(prefix="/api/v1", tags=["analyze"])


class AnalyzeRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=10, ge=1, le=50)
    filters: SearchFilters | None = None
    boosts: SearchBoosts | None = None


class RecommendationResponse(BaseModel):
    category: str
    recommendation: str
    evidence: list[SourceAttribution]


class AnalyzeResponse(BaseModel):
    query: str
    recommendations: list[RecommendationResponse]
    warnings: list[WarningResponse] = Field(default_factory=list)
    degraded: bool = False


def get_recommendation_engine() -> RecommendationEngine:
    return RecommendationEngine()


RetrievalDependency = Annotated[RetrievalService, Depends(get_retrieval_service)]
RecommendationDependency = Annotated[RecommendationEngine, Depends(get_recommendation_engine)]


@router.post("/analyze", response_model=AnalyzeResponse, include_in_schema=False)
async def analyze(
    request: AnalyzeRequest,
    retrieval_service: RetrievalDependency,
    recommendation_engine: RecommendationDependency,
) -> AnalyzeResponse:
    result = await retrieval_service.retrieve(
        request.query,
        limit=request.limit,
        filters=request.filters.as_dict() if request.filters else None,
        boosts=request.boosts.as_dict() if request.boosts else None,
    )
    hits = [hit for hit in result.get("hits", []) if isinstance(hit, RankedHit)]
    recommendations = recommendation_engine.generate(request.query, hits)
    return AnalyzeResponse(
        query=request.query,
        recommendations=[
            RecommendationResponse(
                category=item.category,
                recommendation=item.recommendation,
                evidence=[
                    SourceAttribution(title=evidence.title, url=evidence.source_url)
                    for evidence in item.evidence
                ],
            )
            for item in recommendations
        ],
        warnings=warning_responses(result.get("warnings", [])),
        degraded=bool(result.get("degraded", False)),
    )
