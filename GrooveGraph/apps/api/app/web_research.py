import re
import urllib.robotparser
from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape
from typing import Any, Protocol
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.neo4j_graph import Neo4jGraphService, RelationshipProvenance
from app.rag import SourceDocumentInput, WeaviateRagStore, chunk_document, citation_from_chunk, persist_source_document


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    publisher: str | None = None


@dataclass
class FetchedPage:
    url: str
    html: str
    fetched_at: datetime


@dataclass
class ExtractedSource:
    source_id: str
    url: str
    title: str
    publisher: str | None
    text: str
    fetched_at: datetime
    source_type: str = "web"


@dataclass
class Claim:
    text: str
    source_id: str
    url: str
    title: str
    confidence: float
    evidence_text: str


@dataclass
class ExtractedRelationship:
    from_label: str
    from_id: str
    relationship_type: str
    to_label: str
    to_id: str
    source_id: str
    confidence: float
    evidence_text: str


class WebSearchProvider(Protocol):
    def search(self, query: str, limit: int = 5) -> list[SearchResult]: ...


class HttpSearchProvider:
    def __init__(self, http_client: httpx.Client | None = None) -> None:
        self.http = http_client or httpx.Client(timeout=20)

    @property
    def configured(self) -> bool:
        return bool(settings.tavily_api_key or settings.brave_search_api_key or settings.serpapi_api_key)

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        if settings.tavily_api_key:
            response = self.http.post(
                "https://api.tavily.com/search",
                json={"api_key": settings.tavily_api_key, "query": query, "max_results": limit},
            )
            response.raise_for_status()
            return [
                SearchResult(title=item.get("title", ""), url=item["url"], snippet=item.get("content", ""))
                for item in response.json().get("results", [])
            ]
        if settings.brave_search_api_key:
            response = self.http.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": limit},
                headers={"X-Subscription-Token": settings.brave_search_api_key},
            )
            response.raise_for_status()
            return [
                SearchResult(title=item.get("title", ""), url=item["url"], snippet=item.get("description", ""))
                for item in response.json().get("web", {}).get("results", [])
            ]
        if settings.serpapi_api_key:
            response = self.http.get(
                "https://serpapi.com/search.json",
                params={"q": query, "api_key": settings.serpapi_api_key, "num": limit},
            )
            response.raise_for_status()
            return [
                SearchResult(title=item.get("title", ""), url=item["link"], snippet=item.get("snippet", ""))
                for item in response.json().get("organic_results", [])
                if item.get("link")
            ]
        return []


class WebPageFetcher:
    def __init__(self, http_client: httpx.Client | None = None, cache: dict[str, FetchedPage] | None = None) -> None:
        self.http = http_client or httpx.Client(timeout=20, follow_redirects=True)
        self.cache = cache if cache is not None else {}

    def fetch(self, url: str) -> FetchedPage | None:
        if url in self.cache:
            return self.cache[url]
        if not self._robots_allowed(url):
            return None
        response = self.http.get(url, headers={"User-Agent": settings.musicbrainz_user_agent})
        response.raise_for_status()
        page = FetchedPage(url=url, html=response.text, fetched_at=datetime.now(UTC))
        self.cache[url] = page
        return page

    def _robots_allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        try:
            robots = urllib.robotparser.RobotFileParser(f"{parsed.scheme}://{parsed.netloc}/robots.txt")
            robots.read()
            return robots.can_fetch(settings.musicbrainz_user_agent, url)
        except Exception:
            return True


class SourceExtractor:
    def extract(self, page: FetchedPage, result: SearchResult | None = None) -> ExtractedSource:
        title_match = re.search(r"<title[^>]*>(.*?)</title>", page.html, flags=re.I | re.S)
        title = clean_text(title_match.group(1)) if title_match else result.title if result else page.url
        text = re.sub(r"<(script|style).*?</\1>", " ", page.html, flags=re.I | re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        text = clean_text(unescape(text))
        publisher = result.publisher if result and result.publisher else urlparse(page.url).netloc
        return ExtractedSource(
            source_id=stable_source_id(page.url),
            url=page.url,
            title=title,
            publisher=publisher,
            text=text,
            fetched_at=page.fetched_at,
        )


class ClaimExtractor:
    def extract(self, source: ExtractedSource, topic: str | None = None) -> list[Claim]:
        sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", source.text) if sentence.strip()]
        claims: list[Claim] = []
        for sentence in sentences:
            if len(sentence) < 30:
                continue
            if topic == "lyrics_meaning" and looks_like_full_lyrics(sentence):
                continue
            confidence = 0.78 if any(token in sentence.lower() for token in ["formed", "member", "collaborated", "side project", "performed"]) else 0.5
            claims.append(
                Claim(
                    text=sentence,
                    source_id=source.source_id,
                    url=source.url,
                    title=source.title,
                    confidence=confidence,
                    evidence_text=sentence[:500],
                )
            )
        return claims[:8]


class EntityRelationshipExtractor:
    def extract(self, claims: list[Claim]) -> list[ExtractedRelationship]:
        relationships: list[ExtractedRelationship] = []
        for claim in claims:
            text = claim.text
            side_project = re.search(r"(?P<project>[A-Z][\w '&.-]+) (?:is|was|formed as).*side project.*(?:of|for) (?P<band>[A-Z][\w '&.-]+)", text)
            collaboration = re.search(r"(?P<a>[A-Z][\w '&.-]+) collaborated with (?P<b>[A-Z][\w '&.-]+)", text)
            if side_project:
                relationships.append(
                    ExtractedRelationship(
                        from_label="Project",
                        from_id=slug(side_project.group("project")),
                        relationship_type="SIDE_PROJECT_OF",
                        to_label="Band",
                        to_id=slug(side_project.group("band")),
                        source_id=claim.source_id,
                        confidence=claim.confidence,
                        evidence_text=claim.evidence_text,
                    )
                )
            if collaboration:
                relationships.append(
                    ExtractedRelationship(
                        from_label="Artist",
                        from_id=slug(collaboration.group("a")),
                        relationship_type="COLLABORATED_WITH",
                        to_label="Artist",
                        to_id=slug(collaboration.group("b")),
                        source_id=claim.source_id,
                        confidence=claim.confidence,
                        evidence_text=claim.evidence_text,
                    )
                )
        return relationships


class ResearchPlanner:
    def __init__(
        self,
        search_provider: WebSearchProvider | None = None,
        fetcher: WebPageFetcher | None = None,
        source_extractor: SourceExtractor | None = None,
        claim_extractor: ClaimExtractor | None = None,
        relationship_extractor: EntityRelationshipExtractor | None = None,
    ) -> None:
        self.search_provider = search_provider or HttpSearchProvider()
        self.fetcher = fetcher or WebPageFetcher()
        self.source_extractor = source_extractor or SourceExtractor()
        self.claim_extractor = claim_extractor or ClaimExtractor()
        self.relationship_extractor = relationship_extractor or EntityRelationshipExtractor()

    def build_search_queries(self, question: str, entities: list[str], intent: str) -> list[str]:
        subject = " ".join(entities) if entities else question
        if "primary source interview official" in question:
            return [f"{subject} primary source interview official"]
        if intent == "lyrics_meaning":
            return [
                f"{subject} lyrics meaning official interview",
                f"{subject} song meaning licensed lyrics metadata",
            ]
        if intent == "concerts":
            return [f"{subject} upcoming concerts tour dates official", f"{subject} setlist festival performance"]
        if intent == "side_projects":
            return [f"{subject} side projects members", f"{subject} related bands collaborations"]
        if intent == "band_connections":
            return [f"{subject} band connections collaborations influences"]
        return [f"{subject} band history interview source", f"{subject} collaborations side projects"]

    def research(
        self,
        question: str,
        entities: list[str],
        intent: str,
        *,
        db: Session | None = None,
        rag_store: WeaviateRagStore | None = None,
        graph_service: Neo4jGraphService | None = None,
    ) -> list[dict[str, Any]]:
        if isinstance(self.search_provider, HttpSearchProvider) and not self.search_provider.configured:
            return [
                {
                    "source": "web_research",
                    "reason": "web search not configured",
                    "confidence": 0.0,
                    "evidence_text": "Set TAVILY_API_KEY, BRAVE_SEARCH_API_KEY, or SERPAPI_API_KEY to enable web research.",
                    "citations": [],
                }
            ]

        evidence = self._research_once(question, entities, intent, db=db, rag_store=rag_store, graph_service=graph_service)
        if not evidence or max(item.get("confidence", 0) for item in evidence) < 0.55:
            follow_up = f"{question} primary source interview official"
            evidence.extend(
                self._research_once(follow_up, entities, intent, db=db, rag_store=rag_store, graph_service=graph_service)
            )
        return evidence

    def _research_once(
        self,
        question: str,
        entities: list[str],
        intent: str,
        *,
        db: Session | None,
        rag_store: WeaviateRagStore | None,
        graph_service: Neo4jGraphService | None,
    ) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        for query in self.build_search_queries(question, entities, intent):
            for result in self.search_provider.search(query, limit=3):
                page = self.fetcher.fetch(result.url)
                if page is None:
                    continue
                source = self.source_extractor.extract(page, result)
                claims = self.claim_extractor.extract(source, topic=intent)
                chunks = chunk_document(
                    SourceDocumentInput(
                        source_id=source.source_id,
                        url=source.url,
                        title=source.title,
                        publisher=source.publisher,
                        fetched_at=source.fetched_at,
                        band_names=entities,
                        topic=intent,
                        source_type=source.source_type,
                        provenance="web_research",
                        confidence=max([claim.confidence for claim in claims], default=0.4),
                        text=source.text,
                    )
                )
                if db is not None:
                    persist_source_document(
                        db,
                        SourceDocumentInput(
                            source_id=source.source_id,
                            url=source.url,
                            title=source.title,
                            publisher=source.publisher,
                            fetched_at=source.fetched_at,
                            band_names=entities,
                            topic=intent,
                            source_type=source.source_type,
                            provenance="web_research",
                            confidence=max([claim.confidence for claim in claims], default=0.4),
                            text=source.text,
                        ),
                        chunks,
                    )
                if rag_store is not None and chunks:
                    rag_store.index_chunks(chunks)
                if graph_service is not None:
                    self._upsert_relationships(graph_service, self.relationship_extractor.extract(claims))
                for claim in claims:
                    citation = citation_from_chunk(chunks[0]).model_dump() if chunks else None
                    evidence.append(
                        {
                            "source": "web_research",
                            "source_id": claim.source_id,
                            "reason": claim.text,
                            "confidence": claim.confidence,
                            "evidence_text": claim.evidence_text,
                            "citations": [citation] if citation else [],
                            "query": query,
                        }
                    )
        return evidence

    def _upsert_relationships(self, graph_service: Neo4jGraphService, relationships: list[ExtractedRelationship]) -> None:
        for relationship in relationships:
            graph_service.upsert_node(relationship.from_label, relationship.from_id, name=relationship.from_id.replace("-", " ").title())
            graph_service.upsert_node(relationship.to_label, relationship.to_id, name=relationship.to_id.replace("-", " ").title())
            graph_service.upsert_relationship(
                relationship.from_label,
                relationship.from_id,
                relationship.relationship_type,
                relationship.to_label,
                relationship.to_id,
                RelationshipProvenance(
                    source_id=relationship.source_id,
                    confidence=relationship.confidence,
                    evidence_text=relationship.evidence_text,
                ),
            )


def stable_source_id(url: str) -> str:
    return "web:" + re.sub(r"[^a-zA-Z0-9]+", "-", url.lower()).strip("-")[:160]


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def looks_like_full_lyrics(sentence: str) -> bool:
    lines = sentence.count("\n")
    repeated = len(re.findall(r"\b(chorus|verse|lyrics)\b", sentence.lower()))
    return lines > 8 or repeated > 2 or len(sentence) > 1200
