from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.app.dependencies import get_retrieval_service
from backend.app.retrieval.service import RankedHit, RetrievalService, canonical_source_key


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
    explain: bool = False


class ScoreBreakdown(BaseModel):
    bm25: float
    semantic: float
    fusion: float
    rerank: float | None = None
    final_rank: int
    final_score: float


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
    score_breakdown: ScoreBreakdown | None = None


class SearchResponse(BaseModel):
    hits: list[SearchHitResponse]
    recommendation_categories: list[str]


class AnswerRequest(SearchRequest):
    pass


class AnswerResponse(BaseModel):
    answer: str
    sources: list[SourceAttribution]


RetrievalDependency = Annotated[RetrievalService, Depends(get_retrieval_service)]


@router.post("/search", response_model=SearchResponse, response_model_exclude_none=True)
async def search(request: SearchRequest, retrieval_service: RetrievalDependency) -> SearchResponse:
    result = await retrieval_service.retrieve(
        request.query,
        limit=request.limit,
        filters=request.filters.as_dict() if request.filters else None,
    )
    return SearchResponse(
        hits=[hit_response(hit, include_debug=request.explain) for hit in result.get("hits", [])],
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


def hit_response(hit: object, include_debug: bool = False) -> SearchHitResponse:
    if not isinstance(hit, RankedHit):
        raise TypeError("retrieval result contains an unsupported hit")

    score_breakdown = score_breakdown_response(hit) if include_debug else None
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
        score_breakdown=score_breakdown,
    )


def metadata_value(hit: RankedHit, key: str) -> str | None:
    value = hit.metadata.get(key)
    return str(value) if value is not None else None


def score_breakdown_response(hit: RankedHit) -> ScoreBreakdown:
    return ScoreBreakdown(
        bm25=hit.lexical_score,
        semantic=hit.dense_score,
        fusion=hit.fusion_score,
        rerank=hit.rerank_score,
        final_rank=int(hit.metadata.get("final_rank") or 0),
        final_score=hit.score,
    )


def source_attributions(hits: list[RankedHit]) -> list[SourceAttribution]:
    sources: list[SourceAttribution] = []
    seen: set[str] = set()
    for hit in hits:
        source_key = canonical_source_key(hit.source_url)
        if not hit.source_url or source_key in seen:
            continue
        seen.add(source_key)
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

    evidence = evidence_points(query, hits)
    if not evidence:
        top = hits[0]
        title = metadata_value(top, "title") or metadata_value(top, "heading_path") or "the top source"
        return f"The best grounded answer is in {title}. Open the cited source for the exact implementation details."

    thematic = thematic_answer(query, evidence)
    if thematic:
        return thematic

    lead = f"Based on the strongest matched sources, {lower_first(evidence[0][0])}"
    if len(evidence) == 1:
        return lead

    supporting = " ".join(f"{point} ({title})." for point, title in evidence[1:3])
    return f"{lead} {supporting}".strip()


def thematic_answer(query: str, evidence: list[tuple[str, str]]) -> str | None:
    terms = meaningful_terms(query)
    if {"hybrid", "retrieval"} & terms or {"rerank", "reranking"} & terms:
        source_names = unique_titles(evidence)
        support = f" The top evidence is {', '.join(source_names[:2])}." if source_names else ""
        return (
            "Use a two-stage hybrid retrieval flow: combine lexical/BM25 or structured filtering "
            "with semantic search, then rerank the merged candidates before presenting evidence."
            f"{support}"
        )
    return None


def evidence_points(query: str, hits: list[RankedHit]) -> list[tuple[str, str]]:
    query_terms = meaningful_terms(query)
    points: list[tuple[str, str]] = []
    seen_sentences: set[str] = set()
    for hit in hits:
        title = metadata_value(hit, "title") or metadata_value(hit, "heading_path") or "source"
        for sentence in split_sentences(hit.text):
            sentence = clean_sentence(sentence)
            if query_terms and not any(term in sentence.lower() for term in query_terms):
                continue
            normalized = re.sub(r"\s+", " ", sentence).strip()
            if should_skip_sentence(normalized) or normalized.lower() in seen_sentences:
                continue
            seen_sentences.add(normalized.lower())
            points.append((ensure_sentence(truncate_sentence(normalized)), title))
            break
    return points


def split_sentences(text: str) -> list[str]:
    clean = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    clean = re.sub(r"\s+", " ", clean)
    return [part.strip(" -#*") for part in re.split(r"(?<=[.!?])\s+|\s+-\s+|\s+\*\s+", clean) if part.strip()]


def clean_sentence(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\{\{([^}]+)\}\}", r"\1", text)
    text = re.sub(r"\[([a-z0-9_-]+)\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = text.replace("**", "")
    return re.sub(r"\s+", " ", text).strip()


def should_skip_sentence(text: str) -> bool:
    lower = text.lower()
    if len(text) < 40:
        return True
    if lower.startswith(("blogs", "related content", "see also")):
        return True
    if text.count("http") > 1:
        return True
    if text.count("[") + text.count("]") > 2:
        return True
    return False


def truncate_sentence(text: str, max_chars: int = 260) -> str:
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars].rsplit(" ", 1)[0].rstrip(" ,;:")
    return f"{truncated}..."


def meaningful_terms(query: str) -> set[str]:
    stop_words = {"about", "after", "best", "can", "does", "for", "from", "have", "into", "that", "the", "this", "what", "with", "your"}
    return {term for term in re.findall(r"[a-z0-9]{4,}", query.lower()) if term not in stop_words}


def ensure_sentence(text: str) -> str:
    return text if text.endswith((".", "!", "?")) else f"{text}."


def lower_first(text: str) -> str:
    return text[:1].lower() + text[1:] if text else text


def unique_titles(evidence: list[tuple[str, str]]) -> list[str]:
    titles: list[str] = []
    seen: set[str] = set()
    for _, title in evidence:
        if title not in seen:
            titles.append(title)
            seen.add(title)
    return titles
