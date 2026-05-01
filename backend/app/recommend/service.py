from __future__ import annotations

from dataclasses import dataclass

from backend.app.retrieval.service import RECOMMENDATION_CATEGORIES, RankedHit


@dataclass(frozen=True)
class Evidence:
    title: str
    source_url: str


@dataclass(frozen=True)
class RecommendationOutput:
    category: str
    recommendation: str
    evidence: list[Evidence]


class RecommendationEngine:
    def generate(self, query: str, hits: list[RankedHit]) -> list[RecommendationOutput]:
        evidence = build_evidence(hits)
        if not evidence:
            return []

        return [
            RecommendationOutput(
                category=category,
                recommendation=recommendation_text(category, query, hits),
                evidence=evidence[:2],
            )
            for category in RECOMMENDATION_CATEGORIES
        ]


def build_evidence(hits: list[RankedHit]) -> list[Evidence]:
    evidence: list[Evidence] = []
    seen_urls: set[str] = set()
    for hit in hits:
        if not hit.source_url or hit.source_url in seen_urls:
            continue
        seen_urls.add(hit.source_url)
        evidence.append(
            Evidence(
                title=str(hit.metadata.get("title") or hit.metadata.get("heading_path") or hit.id),
                source_url=hit.source_url,
            )
        )
    return evidence


def recommendation_text(category: str, query: str, hits: list[RankedHit]) -> str:
    top = hits[0] if hits else None
    content_type = str(top.metadata.get("content_type")) if top else "documentation"
    subject = query.strip() or content_type

    templates = {
        "relevance": f"Prioritize {content_type} evidence for '{subject}' and tune boosts toward the highest-scoring grounded sources.",
        "ingestion": f"Ensure canonical metadata and source links are captured for '{subject}' before indexing related chunks.",
        "mapping": f"Add normalized fields for repository, path, heading, content type, and license so '{subject}' can be filtered and boosted predictably.",
        "performance": f"Cache embeddings and reranker inputs for repeated '{subject}' queries, then monitor top-k latency across lexical and dense retrieval.",
        "resiliency": f"Add retries and partial-result handling so '{subject}' recommendations still return evidence when one retrieval backend is unavailable.",
    }
    return templates[category]


def recommendations_as_dicts(recommendations: list[RecommendationOutput]) -> list[dict[str, object]]:
    return [
        {
            "category": recommendation.category,
            "recommendation": recommendation.recommendation,
            "evidence": [
                {"title": evidence.title, "source_url": evidence.source_url}
                for evidence in recommendation.evidence
            ],
        }
        for recommendation in recommendations
    ]

