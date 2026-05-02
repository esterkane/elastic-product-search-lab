from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Annotated, Literal
from urllib.parse import urldefrag

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.app.dependencies import get_retrieval_service
from backend.app.ingest.parser import stable_anchor
from backend.app.ingest.metadata import normalize_boosts, normalize_filters, normalize_metadata
from backend.app.retrieval.service import RankedHit, RetrievalService, RetrievalWarning, canonical_source_key, is_archived_source


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


ChangeTopic = Literal[
    "relevance",
    "ingestion",
    "data_modeling",
    "performance",
    "resilience",
    "esql",
    "vector_search",
    "search_applications",
    "observability",
    "release_notes",
]
TimeRange = Literal["latest", "30d", "90d", "1y", "all"]


TODAY = date.today()


class VersionRange(BaseModel):
    from_: str | None = Field(default=None, alias="from")
    to: str | None = None


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=10, ge=1, le=50)
    filters: SearchFilters | None = None
    boosts: SearchBoosts | None = None
    explain: bool = False
    topic: ChangeTopic | Literal[""] | None = None
    version_range: VersionRange | None = None
    time_range: TimeRange | None = None


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
        limit=retrieval_limit(request),
        filters=request.filters.as_dict() if request.filters else None,
        boosts=request.boosts.as_dict() if request.boosts else None,
    )
    hits = ranked_hits_for_request(result.get("hits", []), request)
    return SearchResponse(
        hits=[hit_response(hit, request.query, include_debug=request.explain) for hit in hits[: request.limit]],
        recommendation_categories=[str(category) for category in result.get("recommendation_categories", [])],
        warnings=warning_responses(result.get("warnings", [])),
        degraded=bool(result.get("degraded", False)),
    )


@router.post("/answer", response_model=AnswerResponse)
async def answer(request: AnswerRequest, retrieval_service: RetrievalDependency) -> AnswerResponse:
    result = await retrieval_service.retrieve(
        request.query,
        limit=retrieval_limit(request),
        filters=request.filters.as_dict() if request.filters else None,
        boosts=request.boosts.as_dict() if request.boosts else None,
    )
    hits = ranked_hits_for_request(result.get("hits", []), request)
    evidence = answer_evidence(request.query, hits, limit=4)
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
        links=answer_links(evidence, limit=4),
        warnings=warning_responses(result.get("warnings", [])),
        degraded=bool(result.get("degraded", False)),
    )


def retrieval_limit(request: SearchRequest) -> int:
    if is_release_request(request):
        return min(max(request.limit * 3, 20), 50)
    return request.limit


def ranked_hits_for_request(raw_hits: object, request: SearchRequest) -> list[RankedHit]:
    hits = [hit for hit in raw_hits if isinstance(hit, RankedHit)] if isinstance(raw_hits, list) else []
    if not is_release_request(request):
        return hits
    return refresh_final_ranks(release_ranked_hits(hits, request))


def refresh_final_ranks(hits: list[RankedHit]) -> list[RankedHit]:
    ranked: list[RankedHit] = []
    for index, hit in enumerate(hits, start=1):
        metadata = dict(hit.metadata)
        metadata["final_rank"] = index
        ranked.append(
            RankedHit(
                id=hit.id,
                score=hit.score,
                metadata=metadata,
                source_url=hit.source_url,
                text=hit.text,
                lexical_score=hit.lexical_score,
                dense_score=hit.dense_score,
                fusion_score=hit.fusion_score,
                rerank_score=hit.rerank_score,
            )
        )
    return ranked


def is_release_request(request: SearchRequest) -> bool:
    return bool(
        request.topic
        or request.version_range
        or request.time_range
        or re.search(r"\b(new|changed|latest|release|8\.|9\.|version|upgrade)\b", request.query, flags=re.IGNORECASE)
    )


TOPIC_TERMS: dict[str, tuple[str, ...]] = {
    "relevance": ("relevance", "ranking", "rerank", "scoring", "bm25", "query rules"),
    "ingestion": ("ingest", "pipeline", "bulk", "failure store", "data freshness", "indexing failure"),
    "data_modeling": ("mapping", "field", "schema", "template", "data model"),
    "performance": ("performance", "latency", "memory", "faster", "throughput", "scaling", "speed"),
    "resilience": ("resilience", "recovery", "retry", "backoff", "circuit breaker", "failure", "bulkhead"),
    "esql": ("es|ql", "esql", "join", "lookup", "query language"),
    "vector_search": ("vector", "semantic", "knn", "dense", "sparse", "rerank", "inference"),
    "search_applications": ("search application", "template", "query rules", "search app"),
    "observability": ("observability", "monitor", "metrics", "profile", "slow log"),
    "release_notes": ("release note", "breaking change", "deprecation", "migration", "what's new"),
}

ENGINEERING_TERMS = (
    "latency",
    "memory",
    "performance",
    "faster",
    "improve",
    "failure",
    "recovery",
    "mapping",
    "pipeline",
    "rerank",
    "vector",
    "join",
    "breaking",
    "deprecation",
    "recall",
    "quality",
    "upgrade",
)

DIRECT_CHANGE_TERMS = (
    "added",
    "adds",
    "changed",
    "deprecated",
    "improved",
    "improves",
    "new",
    "removed",
    "breaking",
    "faster",
    "memory",
    "latency",
    "risk",
)

GENERIC_REFERENCE_TERMS = (
    "overview",
    "getting started",
    "api reference",
    "configuration reference",
    "settings reference",
)


def release_ranked_hits(hits: list[RankedHit], request: SearchRequest) -> list[RankedHit]:
    query_mentions_serverless = "serverless" in request.query.lower()
    decorated = [(release_hit_score(hit, request, query_mentions_serverless), index, hit) for index, hit in enumerate(hits)]
    decorated.sort(key=lambda item: (-item[0], item[1]))
    sorted_hits = [hit for _, _, hit in decorated]
    if query_mentions_serverless:
        return sorted_hits
    non_serverless = [hit for hit in sorted_hits if not hit_mentions_serverless(hit)]
    return non_serverless if non_serverless else sorted_hits


def release_hit_score(hit: RankedHit, request: SearchRequest, query_mentions_serverless: bool) -> float:
    text = hit_text_blob(hit)
    lower = text.lower()
    score = hit.score
    topic = request.topic or infer_topic(request.query)
    if topic:
        topic_terms = TOPIC_TERMS.get(topic, ())
        matches = sum(1 for term in topic_terms if term in lower)
        score += min(matches, 4) * 0.08
    if any(term in lower for term in ENGINEERING_TERMS):
        score += 0.08
    if any(term in lower for term in DIRECT_CHANGE_TERMS):
        score += 0.1
    content_type = str(hit.metadata.get("content_type") or "")
    path = str(hit.metadata.get("path") or "")
    if content_type == "release_note" or "release-notes" in path:
        score += 0.28
    if "highlights" in path or "whats-new" in path:
        score += 0.18
    if content_type == "reference" and not any(term in lower for term in DIRECT_CHANGE_TERMS):
        score -= 0.16
    if any(term in lower for term in GENERIC_REFERENCE_TERMS) and not any(term in lower for term in DIRECT_CHANGE_TERMS):
        score -= 0.18
    if hit.metadata.get("repo") == "elastic/docs-content":
        score += 0.12
    version = extract_version(text)
    if version:
        if version_in_range(version, request.version_range):
            score += 0.16
        elif request.version_range:
            score -= 0.55
        if request.time_range == "latest" and version.startswith("9."):
            score += 0.08
    elif request.version_range:
        score -= 0.12
    if request.time_range and request.time_range != "all":
        hit_date = extract_date_value(text)
        if hit_date and request.time_range == "latest":
            score += hit_date.toordinal() / 10_000_000
        elif hit_date and not date_in_time_range(hit_date, request.time_range):
            score -= 0.32
        elif not hit_date and request.time_range in {"30d", "90d", "1y"}:
            score -= 0.08
    if hit_mentions_serverless(hit) and not query_mentions_serverless:
        score -= 0.65
    if is_archived_source(hit.metadata, hit.source_url):
        score -= 1.0
    return score


def date_in_time_range(hit_date: date, time_range: TimeRange) -> bool:
    windows = {
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
        "1y": timedelta(days=365),
    }
    window = windows.get(time_range)
    return True if window is None else hit_date >= TODAY - window


def hit_text_blob(hit: RankedHit) -> str:
    return " ".join(
        str(value)
        for value in [
            hit.metadata.get("title"),
            hit.metadata.get("heading_path"),
            hit.metadata.get("path"),
            hit.metadata.get("content_type"),
            hit.source_url,
            hit.text[:2000],
        ]
        if value
    )


def hit_mentions_serverless(hit: RankedHit) -> bool:
    return "serverless" in hit_text_blob(hit).lower()


def infer_topic(query: str) -> str | None:
    lower = query.lower()
    for topic, terms in TOPIC_TERMS.items():
        if any(term in lower for term in terms):
            return topic
    return None


def extract_version(text: str) -> str | None:
    match = re.search(r"\b(?:elasticsearch\s*)?([89]\.\d{1,2})(?:\.\d+)?\b", text, flags=re.IGNORECASE)
    return match.group(1) if match else None


def version_in_range(version: str, version_range: VersionRange | None) -> bool:
    if not version_range:
        return True
    value = version_tuple(version)
    lower = version_tuple(version_range.from_, wildcard_high=False) if version_range.from_ else None
    upper = version_tuple(version_range.to, wildcard_high=True) if version_range.to else None
    if lower and value < lower:
        return False
    if upper and value > upper:
        return False
    return True


def version_tuple(version: str | None, wildcard_high: bool = False) -> tuple[int, int]:
    if not version:
        return (0, 0)
    normalized = version.lower().strip().removeprefix("v")
    major, _, minor = normalized.partition(".")
    major_value = int(major) if major.isdigit() else 0
    if minor in {"x", "*"}:
        return (major_value, 999 if wildcard_high else 0)
    return (major_value, int(minor) if minor.isdigit() else 0)


def extract_date_value(text: str) -> date | None:
    match = re.search(r"\b(20\d{2})-(\d{2})-(\d{2})\b", text)
    if not match:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


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
        if is_archived_source(metadata, hit.source_url):
            continue
        source_key = canonical_source_key(hit.source_url)
        if not hit.source_url or source_key in seen:
            continue
        title = metadata_value(metadata, "title") or metadata_value(metadata, "heading_path") or hit.id
        repo = metadata_value(metadata, "repo")
        path = metadata_value(metadata, "path")
        heading_path = metadata_value(metadata, "heading_path")
        excerpt = best_snippet(query, hit.text, title=title, heading_path=heading_path)
        if not excerpt:
            continue
        seen.add(source_key)
        claim = evidence_claim(query, excerpt, title, heading_path)
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
                claim=claim,
                excerpt=excerpt,
                highlight_terms=highlight_terms(query, excerpt),
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
    archive_priority = 1 if is_archived_source(hit.metadata, hit.source_url) else 0
    return (archive_priority, docs_priority, final_rank, -hit.score, hit.id)


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
        direct = intent_direct_answer(query, evidence) or f"No grounded sources were found for '{query}'."
        return {
            "direct_answer": direct,
            "explanation": intent_explanation(query, evidence) or "No source-backed explanation can be produced until retrieval returns evidence.",
            "what_new": None,
            "what_new_items": [],
            "important": why_it_matters(query, evidence) if is_chunk_link_query(query) else "Try a narrower query or sync the indexed sources before searching again.",
            "key_takeaways": key_takeaways(query, evidence) if is_chunk_link_query(query) else ["No grounded evidence was available.", "Sync sources or narrow the query before relying on the answer."],
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
    intent_answer = intent_direct_answer(query, evidence)
    if intent_answer:
        return intent_answer
    primary = evidence[0].claim
    if is_change_query(query):
        return ensure_sentence(primary)
    return ensure_sentence(primary)


def what_new_summary(query: str, evidence: list[AnswerEvidence]) -> str | None:
    if not is_change_query(query):
        return None
    new_terms = ("new", "improve", "improvement", "update", "release", "feature", "workflow", "approach")
    for item in evidence:
        if any(term in item.claim.lower() for term in new_terms):
            return ensure_sentence(item.claim)
    return "The retrieved evidence points to a newer or improved workflow, but no explicit release note was found."


def why_it_matters(query: str, evidence: list[AnswerEvidence]) -> str:
    text = " ".join(item.claim for item in evidence).lower()
    if "rerank" in query.lower() or any("rerank" in item.claim.lower() for item in evidence):
        return "This matters if you run hybrid retrieval or reranking, because it can improve ranking quality after the first retrieval pass while adding latency that needs to be budgeted."
    if "vector" in text or "knn" in text or "semantic" in text:
        return "This matters for vector search because changes can affect recall, memory use, filtered retrieval behavior, and query latency in production workloads."
    if "mapping" in text or "field" in text:
        return "This matters because mapping changes can alter indexing behavior, query semantics, storage cost, and upgrade risk."
    if "pipeline" in text or "ingest" in text or "failure" in text:
        return "This matters because ingest and failure-handling changes affect data freshness, recovery workflows, and how safely you can replay rejected documents."
    if "es|ql" in text or "esql" in text or "join" in text:
        return "This matters because query-language changes can alter execution behavior, latency, and which workloads are safe to move into ES|QL."
    if is_chunk_link_query(query):
        return "This matters because stable chunk metadata lets the UI open the exact documentation section, highlight the relevant passage, and avoid duplicate source cards after reindexing."
    if not evidence:
        return "No grounded evidence was available."
    if "metadata" in query.lower() or "filter" in query.lower():
        return "This matters because consistent metadata makes version, topic, repo, and content-type filtering predictable."
    return "This matters because the selected source describes a concrete Elasticsearch change with engineering impact, not just a generic reference page."


def explanation_from_evidence(query: str, evidence: list[AnswerEvidence]) -> str:
    primary = evidence[0]
    query_explanation = intent_explanation(query, evidence)
    if query_explanation:
        return query_explanation
    if primary.score < 0.015:
        return (
            "The available source is weak for the selected release range. Treat it as a lead, then narrow the topic or version before changing production behavior."
        )
    if len(evidence) == 1:
        return (
            f"{primary.claim} Focus on the section that states the new behavior, any limitation, and the operational tradeoff."
        )
    supporting = evidence[1]
    return (
        f"{primary.claim} The next useful source adds: {supporting.claim} Read them as a short briefing: change first, tradeoff second, implementation detail last."
    )


def what_new_items(query: str, evidence: list[AnswerEvidence]) -> list[str]:
    if not is_change_query(query):
        return []
    items = dedupe_text([ensure_sentence(item.claim) for item in evidence])[:4]
    if len(items) >= 2:
        return items
    if items:
        items.append("The selected sources point to the newest meaningful change in the chosen version range.")
    return items


def key_takeaways(query: str, evidence: list[AnswerEvidence]) -> list[str]:
    if is_chunk_link_query(query):
        return [
            "Store repo, path, heading, anchor, license, content type, source_url, and reader_url with every chunk.",
            "Use deterministic chunk IDs so unchanged documentation is not reindexed as duplicate evidence.",
            "Prefer section-level links over page-level links when the heading anchor is available.",
        ]
    if not evidence:
        return ["No grounded evidence was available."]
    primary = evidence[0]
    takeaways = [
        f"Open {primary.title} first and inspect the section that describes the behavior change.",
        why_it_matters(query, evidence),
    ]
    if len(evidence) > 1:
        takeaways.append("Use related sources only when they add an example, caveat, or implementation detail.")
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


def is_chunk_link_query(query: str) -> bool:
    lower = query.lower()
    return (
        any(term in lower for term in ("chunk", "chunks", "chunking", "index documentation", "index docs"))
        and any(term in lower for term in ("stable", "source link", "source links", "provenance", "canonical"))
    )


def intent_direct_answer(query: str, evidence: list[AnswerEvidence]) -> str | None:
    if is_chunk_link_query(query):
        return (
            "Index documentation as section-aware chunks with canonical repo, file path, heading, stable anchor, "
            "license, content type, and both reader and source URLs stored on every chunk."
        )
    return None


def intent_explanation(query: str, evidence: list[AnswerEvidence]) -> str | None:
    if is_chunk_link_query(query):
        source_hint = evidence[0].title if evidence else "the strongest indexed source"
        return (
            f"Use {source_hint} as the first source to verify the linking behavior, then store enough metadata "
            "for each chunk to rebuild the user-facing docs URL and the GitHub provenance URL independently. "
            "That makes search results stable across syncs and lets the answer UI highlight the exact passage "
            "instead of showing only a raw file path."
        )
    return None


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


def best_snippet(
    query: str,
    text: str,
    max_chars: int = 360,
    title: str | None = None,
    heading_path: str | None = None,
) -> str | None:
    sentences = [clean_sentence(sentence) for sentence in split_sentences(text)]
    sentences = [
        sentence
        for sentence in sentences
        if not should_skip_sentence(sentence) and not is_boilerplate_sentence(sentence, title, heading_path)
    ]
    if not sentences:
        cleaned = clean_evidence_sentence(text, title, heading_path)
        if is_boilerplate_sentence(cleaned, title, heading_path):
            return None
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


def evidence_claim(query: str, excerpt: str, title: str, heading_path: str | None) -> str:
    cleaned = clean_evidence_sentence(excerpt, title, heading_path)
    if is_chunk_link_query(query):
        return "This source is relevant to stable documentation links and should be checked for the exact section or link syntax."
    return cleaned


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
    text = re.sub(r":::\{[^}]+\}|:::", " ", text)
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\{\{([^}]+)\}\}", r"\1", text)
    text = re.sub(r"\[([a-z0-9_-]+)\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = text.replace("**", "")
    text = re.sub(r"\s*[✅❌]\s*", " ", text)
    text = re.sub(r"\b(open|dos|don ts)\b[: ]*", " ", text, flags=re.IGNORECASE)
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


def is_boilerplate_sentence(text: str, title: str | None = None, heading_path: str | None = None) -> bool:
    cleaned = clean_evidence_sentence(text, title, heading_path)
    if not cleaned:
        return True
    lower = cleaned.lower().strip(" .")
    if lower in {"documentation", "overview"}:
        return True
    if re.fullmatch(r"[a-z0-9 /_&-]+ (documentation|guide|lab)", lower):
        return True
    if title and normalized_text(cleaned) in {
        normalized_text(title),
        normalized_text(f"{title} documentation"),
        normalized_text(f"{title} guide"),
        normalized_text(f"{title} lab"),
    }:
        return True
    heading = heading_path.split(">")[-1].strip() if heading_path else None
    if heading_path and normalized_text(cleaned) in {
        normalized_text(heading_path),
        normalized_text(f"{heading_path} documentation"),
        normalized_text(f"{heading_path} guide"),
        normalized_text(f"{heading_path} lab"),
    }:
        return True
    if heading and normalized_text(cleaned) in {
        normalized_text(heading),
        normalized_text(f"{heading} documentation"),
        normalized_text(f"{heading} guide"),
        normalized_text(f"{heading} lab"),
    }:
        return True
    return False


def clean_evidence_sentence(text: str, title: str | None = None, heading_path: str | None = None) -> str:
    cleaned = clean_sentence(text)
    prefixes = [value for value in [title, heading_path, heading_path.split(">")[-1].strip() if heading_path else None] if value]
    for prefix in prefixes:
        prefix_clean = clean_sentence(prefix)
        if not prefix_clean:
            continue
        duplicated = f"{prefix_clean} {prefix_clean}"
        if cleaned.lower().startswith(duplicated.lower()):
            cleaned = cleaned[len(prefix_clean):].strip()
        breadcrumb = f"{prefix_clean} > {prefix_clean}"
        if cleaned.lower().startswith(breadcrumb.lower()):
            cleaned = cleaned[len(breadcrumb):].strip(" .:-")
        doc_suffix = f"{prefix_clean} documentation"
        if normalized_text(cleaned) == normalized_text(doc_suffix):
            return ""
        guide_suffix = f"{prefix_clean} guide"
        if normalized_text(cleaned) == normalized_text(guide_suffix):
            return ""
        lab_suffix = f"{prefix_clean} lab"
        if normalized_text(cleaned) == normalized_text(lab_suffix):
            return ""
    if heading_path and normalized_text(cleaned) in {
        normalized_text(heading_path),
        normalized_text(f"{heading_path} documentation"),
        normalized_text(f"{heading_path} guide"),
        normalized_text(f"{heading_path} lab"),
    }:
        return ""
    return ensure_sentence(cleaned) if cleaned else ""


def normalized_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def truncate_sentence(text: str, max_chars: int = 260) -> str:
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars].rsplit(" ", 1)[0].rstrip(" ,;:")
    return f"{truncated}..."


def meaningful_terms(query: str) -> set[str]:
    stop_words = {
        "about",
        "after",
        "best",
        "can",
        "does",
        "documentation",
        "docs",
        "for",
        "from",
        "have",
        "into",
        "that",
        "the",
        "this",
        "what",
        "with",
        "your",
    }
    terms = {term for term in re.findall(r"[a-z0-9]{4,}", query.lower()) if term not in stop_words}
    if is_chunk_link_query(query):
        terms.update({"anchor", "heading", "link", "links", "page", "path", "section", "source"})
    return terms


def ensure_sentence(text: str) -> str:
    return text if text.endswith((".", "!", "?")) else f"{text}."


def lower_first(text: str) -> str:
    return text[:1].lower() + text[1:] if text else text
