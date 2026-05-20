from datetime import UTC, datetime

from app.web_research import (
    Claim,
    ClaimExtractor,
    EntityRelationshipExtractor,
    ExtractedSource,
    FetchedPage,
    ResearchPlanner,
    SearchResult,
    SourceExtractor,
    WebPageFetcher,
)


class FakeSearchProvider:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        self.queries.append(query)
        return [SearchResult(title="Radiohead interview", url=f"https://example.com/{len(self.queries)}")]


class FakeFetcher:
    def fetch(self, url: str) -> FetchedPage:
        return FetchedPage(
            url=url,
            html="<html><title>Radiohead interview</title><body>The Smile is a side project of Radiohead. Thom Yorke collaborated with Flea.</body></html>",
            fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


class WeakClaimExtractor:
    def extract(self, source: ExtractedSource, topic: str | None = None) -> list[Claim]:
        return [
            Claim(
                text="A vague, weakly supported music claim.",
                source_id=source.source_id,
                url=source.url,
                title=source.title,
                confidence=0.2,
                evidence_text="A vague, weakly supported music claim.",
            )
        ]


def test_search_query_generation() -> None:
    planner = ResearchPlanner(search_provider=FakeSearchProvider(), fetcher=FakeFetcher())

    lyrics = planner.build_search_queries("What do the lyrics mean?", ["Radiohead"], "lyrics_meaning")
    side_projects = planner.build_search_queries("What side projects?", ["Pixies"], "side_projects")

    assert lyrics == [
        "Radiohead lyrics meaning official interview",
        "Radiohead song meaning licensed lyrics metadata",
    ]
    assert side_projects == [
        "Pixies side projects members",
        "Pixies related bands collaborations",
    ]


def test_source_extraction_readable_text() -> None:
    source = SourceExtractor().extract(
        FetchedPage(
            url="https://example.com/radiohead",
            html="<html><head><title>Radiohead Bio</title><style>.x{}</style></head><body><h1>Radiohead</h1><p>Band history text.</p></body></html>",
            fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )

    assert source.title == "Radiohead Bio"
    assert source.publisher == "example.com"
    assert "Band history text." in source.text
    assert ".x{}" not in source.text


def test_claim_extraction_with_citations() -> None:
    planner = ResearchPlanner(search_provider=FakeSearchProvider(), fetcher=FakeFetcher())

    evidence = planner.research("Radiohead side projects", ["Radiohead"], "side_projects")

    assert evidence
    assert evidence[0]["source"] == "web_research"
    assert evidence[0]["source_id"].startswith("web:")
    assert evidence[0]["citations"][0]["title"] == "Radiohead interview"
    assert evidence[0]["confidence"] >= 0.55


def test_entity_relationship_extraction() -> None:
    claim = Claim(
        text="The Smile is a side project of Radiohead.",
        source_id="source-1",
        url="https://example.com",
        title="Source",
        confidence=0.8,
        evidence_text="The Smile is a side project of Radiohead.",
    )

    relationships = EntityRelationshipExtractor().extract([claim])

    assert len(relationships) == 1
    assert relationships[0].from_label == "Project"
    assert relationships[0].from_id == "the-smile"
    assert relationships[0].relationship_type == "SIDE_PROJECT_OF"
    assert relationships[0].to_id == "radiohead"


def test_weak_evidence_triggers_follow_up_retrieval_pass() -> None:
    search = FakeSearchProvider()
    planner = ResearchPlanner(
        search_provider=search,
        fetcher=FakeFetcher(),
        claim_extractor=WeakClaimExtractor(),
    )

    evidence = planner.research("Radiohead disputed claim", ["Radiohead"], "band_history")

    assert evidence
    assert len(search.queries) > len(planner.build_search_queries("Radiohead disputed claim", ["Radiohead"], "band_history"))
    assert any("primary source interview official" in query for query in search.queries)
