from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.app.dependencies import get_retrieval_service
from backend.app.ingest.metadata import normalize_boosts, normalize_filters, normalize_metadata
from backend.app.retrieval.service import RankedHit, RetrievalService, RetrievalWarning, canonical_source_key


router = APIRouter(prefix="/api/v1", tags=["search"])


class SearchFilters(BaseModel):
    repo: str | None = None
    path: str | None = None
    heading_path: str | None = None
    content_type: str | None = None
    license_family: str | None = None

    def as_dict(self) -> dict[str, str]:
        return normalize_filters({
            key: value
            for key, value in {
                "repo": self.repo,
                "path": self.path,
                "heading_path": self.heading_path,
                "content_type": self.content_type,
                "license_family": self.license_family,
            }.items()
            if value
        }) or {}


class SearchBoosts(BaseModel):
    repo: dict[str, float] | None = None
    path: dict[str, float] | None = None
    heading_path: dict[str, float] | None = None
    content_type: dict[str, float] | None = None
    license_family: dict[str, float] | None = None

    def as_dict(self) -> dict[str, dict[str, float]]:
        return normalize_boosts({
            key: value
            for key, value in {
                "repo": self.repo,
                "path": self.path,
                "heading_path": self.heading_path,
                "content_type": self.content_type,
                "license_family": self.license_family,
            }.items()
            if value
        })


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=10, ge=1, le=50)
    filters: SearchFilters | None = None
    boosts: SearchBoosts | None = None
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


class WarningResponse(BaseModel):
    code: str
    message: str
    stage: str


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
    snippet: str | None = None
    highlights: list[str] = Field(default_factory=list)
    match_reason: str | None = None
    score_breakdown: ScoreBreakdown | None = None


class SearchResponse(BaseModel):
    hits: list[SearchHitResponse]
    recommendation_categories: list[str]
    warnings: list[WarningResponse] = Field(default_factory=list)
    degraded: bool = False


class AnswerRequest(SearchRequest):
    pass


class AnswerResponse(BaseModel):
    answer: str
    sources: list[SourceAttribution]
    warnings: list[WarningResponse] = Field(default_factory=list)
    degraded: bool = False


RetrievalDependency = Annotated[RetrievalService, Depends(get_retrieval_service)]


@router.post("/search", response_model=SearchResponse, response_model_exclude_none=True)
async def search(request: SearchRequest, retrieval_service: RetrievalDependency) -> SearchResponse:
    result = await retrieval_service.retrieve(
        request.query,
        limit=request.limit,
        filters=request.filters.as_dict() if request.filters else None,
        boosts=request.boosts.as_dict() if request.boosts else None,
    )
    return SearchResponse(
        hits=[hit_response(hit, request.query, include_debug=request.explain) for hit in result.get("hits", [])],
        recommendation_categories=[str(category) for category in result.get("recommendation_categories", [])],
        warnings=warning_responses(result.get("warnings", [])),
        degraded=bool(result.get("degraded", False)),
    )


@router.post("/answer", response_model=AnswerResponse)
async def answer(request: AnswerRequest, retrieval_service: RetrievalDependency) -> AnswerResponse:
    result = await retrieval_service.retrieve(
        request.query,
        limit=request.limit,
        filters=request.filters.as_dict() if request.filters else None,
        boosts=request.boosts.as_dict() if request.boosts else None,
    )
    hits = [hit for hit in result.get("hits", []) if isinstance(hit, RankedHit)]
    sources = source_attributions(hits)
    return AnswerResponse(
        answer=synthesize_answer(request.query, hits),
        sources=sources,
        warnings=warning_responses(result.get("warnings", [])),
        degraded=bool(result.get("degraded", False)),
    )


def hit_response(hit: object, query: str, include_debug: bool = False) -> SearchHitResponse:
    if not isinstance(hit, RankedHit):
        raise TypeError("retrieval result contains an unsupported hit")

    score_breakdown = score_breakdown_response(hit) if include_debug else None
    metadata = normalize_metadata(hit.metadata, source_url=hit.source_url)
    return SearchHitResponse(
        id=hit.id,
        score=hit.score,
        title=metadata_value(metadata, "title"),
        repo=metadata_value(metadata, "repo"),
        path=metadata_value(metadata, "path"),
        heading_path=metadata_value(metadata, "heading_path"),
        content_type=metadata_value(metadata, "content_type"),
        license_family=metadata_value(metadata, "license_family"),
        source_url=hit.source_url,
        snippet=best_snippet(query, hit.text),
        highlights=highlight_terms(query, hit.text),
        match_reason=match_reason(hit),
        score_breakdown=score_breakdown,
    )


def metadata_value(metadata: dict, key: str) -> str | None:
    value = metadata.get(key)
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
                title=metadata_value(hit.metadata, "title") or metadata_value(hit.metadata, "heading_path") or hit.id,
                url=hit.source_url,
            )
        )
    return sources


def warning_responses(warnings: object) -> list[WarningResponse]:
    output: list[WarningResponse] = []
    if not isinstance(warnings, list):
        return output
    for warning in warnings:
        if isinstance(warning, RetrievalWarning):
            output.append(WarningResponse(code=warning.code, message=warning.message, stage=warning.stage))
        elif isinstance(warning, dict):
            output.append(
                WarningResponse(
                    code=str(warning.get("code") or "warning"),
                    message=str(warning.get("message") or "Retrieval warning."),
                    stage=str(warning.get("stage") or "retrieval"),
                )
            )
    return output


def synthesize_answer(query: str, hits: list[RankedHit]) -> str:
    if not hits:
        return f"No grounded sources were found for '{query}'."

    evidence = evidence_points(query, hits)
    if not evidence:
        top = hits[0]
        title = metadata_value(top.metadata, "title") or metadata_value(top.metadata, "heading_path") or "the top source"
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
        support = f" Grounded by {', '.join(source_names[:2])}." if source_names else ""
        detail = f" {evidence[0][0]}" if evidence else ""
        return (
            "Use hybrid retrieval to build a strong candidate pool, then rerank only the small top-k set "
            "when final precision matters more than raw latency."
            f"{detail}{support}"
        )
    return None


def evidence_points(query: str, hits: list[RankedHit]) -> list[tuple[str, str]]:
    query_terms = meaningful_terms(query)
    points: list[tuple[str, str]] = []
    seen_sentences: set[str] = set()
    for hit in hits:
        title = metadata_value(hit.metadata, "title") or metadata_value(hit.metadata, "heading_path") or "source"
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


def best_snippet(query: str, text: str, max_chars: int = 360) -> str | None:
    sentences = [clean_sentence(sentence) for sentence in split_sentences(text)]
    sentences = [sentence for sentence in sentences if not should_skip_sentence(sentence)]
    if not sentences:
        cleaned = clean_sentence(text)
        return truncate_sentence(cleaned, max_chars=max_chars) if cleaned else None

    terms = meaningful_terms(query)
    if terms:
        scored = sorted(
            (
                (
                    sum(1 for term in terms if term in sentence.lower()),
                    min(len(sentence), max_chars),
                    sentence,
                )
                for sentence in sentences
            ),
            key=lambda item: (-item[0], -item[1], item[2]),
        )
        if scored and scored[0][0] > 0:
            return truncate_sentence(ensure_sentence(scored[0][2]), max_chars=max_chars)
    return truncate_sentence(ensure_sentence(sentences[0]), max_chars=max_chars)


def highlight_terms(query: str, text: str, max_terms: int = 6) -> list[str]:
    terms = meaningful_terms(query)
    lower_text = clean_sentence(text).lower()
    matched = sorted(term for term in terms if term in lower_text)
    return matched[:max_terms]


def match_reason(hit: RankedHit) -> str:
    channels: list[str] = []
    if hit.lexical_score > 0:
        channels.append("keyword/BM25")
    if hit.dense_score > 0:
        channels.append("semantic")
    if hit.rerank_score is not None:
        channels.append("reranked")
    if not channels:
        channels.append("metadata")
    heading = metadata_value(hit.metadata, "heading_path") or metadata_value(hit.metadata, "title")
    location = f" in {heading}" if heading else ""
    return f"Matched by {', '.join(channels)} evidence{location}."


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
