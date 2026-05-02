from __future__ import annotations

import re
from typing import Annotated, Literal
from urllib.parse import urldefrag

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.app.dependencies import get_retrieval_service
from backend.app.ingest.parser import stable_anchor
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


LinkLabel = Literal["Read documentation", "View source"]
ConfidenceLevel = Literal["high", "medium", "low"]
EvidenceRole = Literal["primary", "supporting"]


class AnswerEvidence(BaseModel):
    title: str
    heading_path: str | None = None
    repo: str | None = None
    path: str | None = None
    content_type: str | None = None
    license_family: str | None = None
    score: float = 0
    role: EvidenceRole = "supporting"
    claim: str
    excerpt: str
    highlight_terms: list[str]
    reader_url: str
    source_url: str
    link_label: LinkLabel


class AnswerLink(BaseModel):
    title: str
    url: str
    link_label: LinkLabel
    repo: str | None = None
    path: str | None = None
    heading_path: str | None = None


class SourceProvenance(BaseModel):
    title: str
    repo: str | None = None
    path: str | None = None
    heading_path: str | None = None
    source_url: str
    reader_url: str


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
    summary: str
    direct_answer: str
    explanation: str
    what_new: str | None = None
    what_new_items: list[str] = Field(default_factory=list)
    important: str | None = None
    key_takeaways: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel
    best_source: AnswerLink | None = None
    supporting_sources: list[AnswerLink] = Field(default_factory=list)
    evidence_quotes: list[str] = Field(default_factory=list)
    provenance: list[SourceProvenance] = Field(default_factory=list)
    evidence: list[AnswerEvidence]
    links: list[AnswerLink]
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
    evidence = answer_evidence(request.query, hits, limit=3)
    answer_model = synthesize_answer_model(request.query, evidence)
    return AnswerResponse(
        summary=answer_model["direct_answer"],
        direct_answer=answer_model["direct_answer"],
        explanation=answer_model["explanation"],
        what_new=answer_model["what_new"],
        what_new_items=answer_model["what_new_items"],
        important=answer_model["important"],
        key_takeaways=answer_model["key_takeaways"],
        confidence=answer_model["confidence"],
        best_source=answer_model["best_source"],
        supporting_sources=answer_model["supporting_sources"],
        evidence_quotes=answer_model["evidence_quotes"],
        provenance=answer_model["provenance"],
        evidence=evidence,
        links=answer_links(evidence, limit=3),
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


def answer_evidence(query: str, hits: list[RankedHit], limit: int = 3) -> list[AnswerEvidence]:
    evidence: list[AnswerEvidence] = []
    seen: set[str] = set()
    for hit in sorted(hits, key=evidence_sort_key):
        metadata = normalize_metadata(hit.metadata, source_url=hit.source_url)
        source_key = canonical_source_key(hit.source_url)
        if not hit.source_url or source_key in seen:
            continue
        excerpt = best_snippet(query, hit.text)
        if not excerpt:
            continue
        seen.add(source_key)
        title = metadata_value(metadata, "title") or metadata_value(metadata, "heading_path") or hit.id
        repo = metadata_value(metadata, "repo")
        path = metadata_value(metadata, "path")
        heading_path = metadata_value(metadata, "heading_path")
        content_type = metadata_value(metadata, "content_type")
        license_family = metadata_value(metadata, "license_family")
        reader_url = reader_url_for(metadata, hit.source_url)
        link_label: LinkLabel = "Read documentation" if reader_url != hit.source_url else "View source"
        role: EvidenceRole = "primary" if not evidence else "supporting"
        evidence.append(
            AnswerEvidence(
                title=title,
                heading_path=heading_path,
                repo=repo,
                path=path,
                content_type=content_type,
                license_family=license_family,
                score=hit.score,
                role=role,
                claim=excerpt,
                excerpt=excerpt,
                highlight_terms=highlight_terms(query, hit.text),
                reader_url=reader_url,
                source_url=hit.source_url,
                link_label=link_label,
            )
        )
        if len(evidence) >= limit:
            break
    return evidence


def evidence_sort_key(hit: RankedHit) -> tuple[int, int, float, str]:
    repo = str(hit.metadata.get("repo") or "")
    final_rank = int(hit.metadata.get("final_rank") or 9999)
    docs_priority = 0 if repo == "elastic/docs-content" else 1
    return (docs_priority, final_rank, -hit.score, hit.id)


def answer_links(evidence: list[AnswerEvidence], limit: int = 3) -> list[AnswerLink]:
    links: list[AnswerLink] = []
    seen: set[str] = set()
    for item in evidence:
        url = item.reader_url or item.source_url
        if url in seen:
            continue
        seen.add(url)
        links.append(
            AnswerLink(
                title=item.title,
                url=url,
                link_label=item.link_label,
                repo=item.repo,
                path=item.path,
                heading_path=item.heading_path,
            )
        )
        if len(links) >= limit:
            break
    return links


def synthesize_answer(query: str, evidence: list[AnswerEvidence]) -> str:
    return synthesize_answer_model(query, evidence)["direct_answer"]


def synthesize_answer_model(query: str, evidence: list[AnswerEvidence]) -> dict:
    if not evidence:
        direct = f"No grounded sources were found for '{query}'."
        return {
            "direct_answer": direct,
            "explanation": "No source-backed explanation can be produced until retrieval returns evidence.",
            "what_new": None,
            "what_new_items": [],
            "important": "Try a narrower query or sync the indexed sources before searching again.",
            "key_takeaways": ["No grounded evidence was available.", "Sync sources or narrow the query before relying on the answer."],
            "confidence": "low",
            "best_source": None,
            "supporting_sources": [],
            "evidence_quotes": [],
            "provenance": [],
        }

    direct = direct_answer_from_evidence(query, evidence)
    links = answer_links(evidence, limit=3)
    return {
        "direct_answer": direct,
        "explanation": explanation_from_evidence(query, evidence),
        "what_new": what_new_summary(query, evidence),
        "what_new_items": what_new_items(query, evidence),
        "important": why_it_matters(query, evidence),
        "key_takeaways": key_takeaways(query, evidence),
        "confidence": confidence_level(evidence),
        "best_source": links[0] if links else None,
        "supporting_sources": links[1:],
        "evidence_quotes": dedupe_text([item.excerpt for item in evidence])[:3],
        "provenance": [
            SourceProvenance(
                title=item.title,
                repo=item.repo,
                path=item.path,
                heading_path=item.heading_path,
                source_url=item.source_url,
                reader_url=item.reader_url,
            )
            for item in evidence
        ],
    }


def direct_answer_from_evidence(query: str, evidence: list[AnswerEvidence]) -> str:
    primary = evidence[0].claim
    if is_change_query(query):
        return f"The clearest update: {primary}"
    return f"The best answer is: {primary}"


def what_new_summary(query: str, evidence: list[AnswerEvidence]) -> str | None:
    if not is_change_query(query):
        return None
    new_terms = ("new", "improve", "improvement", "update", "release", "feature", "workflow", "approach")
    for item in evidence:
        if any(term in item.claim.lower() for term in new_terms):
            return ensure_sentence(item.claim)
    return "The retrieved evidence points to a newer or improved workflow, but no explicit release note was found."


def why_it_matters(query: str, evidence: list[AnswerEvidence]) -> str:
    if not evidence:
        return "No grounded evidence was available."
    if "rerank" in query.lower() or any("rerank" in item.claim.lower() for item in evidence):
        return "This matters because reranking can improve final precision after hybrid retrieval has already found a useful candidate pool."
    if "metadata" in query.lower() or "filter" in query.lower():
        return "This matters because consistent metadata makes source filtering, provenance, and answer grounding predictable."
    return "This matters because the answer is tied to specific documentation sections and source provenance instead of unsupported generated text."


def explanation_from_evidence(query: str, evidence: list[AnswerEvidence]) -> str:
    primary = evidence[0]
    source_family = "Elastic documentation" if primary.repo == "elastic/docs-content" else "Elastic source material"
    if primary.score < 0.015:
        return (
            f"The best match is weak, so treat this as supporting context from {source_family}. "
            "The result indicates the likely topic area, but you should verify the cited source before acting on it."
        )
    if len(evidence) == 1:
        return (
            f"The primary source says: {primary.claim} This is the main grounded result for the query, "
            f"and it comes from {source_family}."
        )
    supporting = evidence[1]
    return (
        f"The primary source says: {primary.claim} A supporting source adds: {supporting.claim} "
        "Together, these sources give the answer and show where to verify it without relying on repeated snippets."
    )


def what_new_items(query: str, evidence: list[AnswerEvidence]) -> list[str]:
    if not is_change_query(query):
        return []
    items = dedupe_text([ensure_sentence(item.claim) for item in evidence])[:4]
    if len(items) >= 2:
        return items
    if items:
        items.append("The retrieved sources point to the most relevant changed or improved workflow for this query.")
    return items


def key_takeaways(query: str, evidence: list[AnswerEvidence]) -> list[str]:
    if not evidence:
        return ["No grounded evidence was available."]
    primary = evidence[0]
    takeaways = [
        f"Open {primary.title} first; it is the primary proof for this answer.",
        why_it_matters(query, evidence),
    ]
    if len(evidence) > 1:
        takeaways.append("Use the supporting evidence to confirm related workflows or edge cases.")
    return dedupe_text(takeaways)[:3]


def confidence_level(evidence: list[AnswerEvidence]) -> ConfidenceLevel:
    if len(evidence) >= 2 and evidence[0].score >= 0.03:
        return "high"
    if evidence and evidence[0].score >= 0.015:
        return "medium"
    return "low"


def is_change_query(query: str) -> bool:
    return any(
        term in query.lower()
        for term in ("new", "what changed", "change", "changed", "improve", "improvement", "release", "feature", "update")
    )


def dedupe_text(items: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for item in items:
        key = re.sub(r"\W+", " ", item.lower()).strip()
        if key and key not in seen:
            seen.add(key)
            output.append(item)
    return output


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


def reader_url_for(metadata: dict, source_url: str) -> str:
    repo = metadata_value(metadata, "repo")
    path = metadata_value(metadata, "path")
    if repo != "elastic/docs-content" or not path:
        return source_url

    reader_path = path.replace("\\", "/")
    reader_path = re.sub(r"\.mdx?$", "", reader_path, flags=re.IGNORECASE).strip("/")
    anchor = metadata_value(metadata, "anchor") or source_anchor(source_url) or heading_anchor(metadata)
    url = f"https://www.elastic.co/docs/{reader_path}"
    return f"{url}#{anchor}" if anchor else url


def source_anchor(source_url: str) -> str | None:
    fragment = urldefrag(source_url).fragment.strip()
    return fragment or None


def heading_anchor(metadata: dict) -> str | None:
    heading_path = metadata_value(metadata, "heading_path")
    if not heading_path:
        return None
    heading = heading_path.split(">")[-1].strip()
    return stable_anchor(heading)


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
