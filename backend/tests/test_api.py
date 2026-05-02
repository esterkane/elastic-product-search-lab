from fastapi.testclient import TestClient

from backend.app.api.admin import get_ingestion_service
from backend.app.dependencies import build_retrieval_service, get_async_engine
from backend.app.api.search import answer_evidence, answer_links, get_retrieval_service, reader_url_for, synthesize_answer
from backend.app.main import create_app
from backend.app.retrieval.service import RankedHit, RetrievalWarning


class FakeRetrievalService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        filters: dict | None = None,
        boosts: dict | None = None,
    ) -> dict[str, object]:
        self.calls.append({"query": query, "limit": limit, "filters": filters, "boosts": boosts})
        return {
            "hits": [
                RankedHit(
                    id="chunk-1",
                    score=0.97,
                    metadata={
                        "repo": "elastic/docs-content",
                        "path": "guide/page.md",
                        "title": "Hybrid search notebook",
                        "heading_path": "Guide > Hybrid",
                        "content_type": "guide",
                        "license_family": "elastic-license",
                        "final_rank": 1,
                    },
                    source_url="https://example.test/hybrid#combine",
                    text="Combine lexical and dense retrieval, then rerank the merged candidate set before presenting evidence.",
                    lexical_score=0.42,
                    dense_score=0.61,
                    fusion_score=0.53,
                    rerank_score=0.88,
                ),
                RankedHit(
                    id="chunk-2",
                    score=0.72,
                    metadata={
                        "repo": "elastic/docs-content",
                        "path": "rules/page.md",
                        "title": "Query rules notebook",
                        "heading_path": "Guide > Rules",
                        "content_type": "guide",
                        "license_family": "elastic-license",
                        "final_rank": 2,
                    },
                    source_url="https://example.test/rules",
                    text="Use query rules for curated boosts.",
                    lexical_score=0.35,
                    dense_score=0.22,
                    fusion_score=0.41,
                    rerank_score=0.72,
                ),
                RankedHit(
                    id="chunk-3",
                    score=0.68,
                    metadata={
                        "repo": "elastic/docs-content",
                        "path": "guide/page.md",
                        "title": "Hybrid search notebook",
                        "heading_path": "Guide > Hybrid follow-up",
                        "content_type": "guide",
                        "license_family": "elastic-license",
                        "final_rank": 3,
                    },
                    source_url="https://example.test/hybrid#rerank",
                    text="Reranking helps choose the most useful evidence after hybrid retrieval returns overlapping candidates.",
                    lexical_score=0.2,
                    dense_score=0.58,
                    fusion_score=0.39,
                    rerank_score=0.68,
                ),
            ],
            "recommendation_categories": ["relevance", "ingestion", "mapping", "performance", "resiliency"],
            "warnings": [],
            "degraded": False,
        }


class FakeIngestionService:
    async def ingest_repo(self, request):
        return {
            "status": "completed",
            "repo_url": request.repo_url,
            "branch": request.branch,
            "message": "Ingested for test.",
        }


def make_client() -> tuple[TestClient, FakeRetrievalService]:
    app = create_app()
    retrieval = FakeRetrievalService()
    app.dependency_overrides[get_retrieval_service] = lambda: retrieval
    app.dependency_overrides[get_ingestion_service] = lambda: FakeIngestionService()
    return TestClient(app), retrieval


def test_health_and_metrics_endpoints() -> None:
    client, _ = make_client()

    assert client.get("/api/v1/health").json() == {"status": "ok", "service": "elastic-repo-inventory"}
    metrics = client.get("/api/v1/metrics").json()
    assert metrics["recommendation_categories"] == ["relevance", "ingestion", "mapping", "performance", "resiliency"]
    assert metrics["endpoints"]["answer"] == "POST /api/v1/answer"


def test_search_endpoint_supports_optional_filters() -> None:
    client, retrieval = make_client()

    response = client.post(
        "/api/v1/search",
        json={
            "query": "hybrid retrieval",
            "limit": 2,
            "filters": {"repo": "elastic/docs-content", "content_type": "guide"},
            "boosts": {"content_type": {"documentation": 0.15}},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["hits"][0]["title"] == "Hybrid search notebook"
    assert body["hits"][0]["source_url"] == "https://example.test/hybrid#combine"
    assert body["hits"][0]["snippet"] == "Combine lexical and dense retrieval, then rerank the merged candidate set before presenting evidence."
    assert body["hits"][0]["highlights"] == ["retrieval"]
    assert body["hits"][0]["match_reason"] == "Matched by keyword/BM25, semantic, reranked evidence in Guide > Hybrid."
    assert "score_breakdown" not in body["hits"][0]
    assert body["warnings"] == []
    assert body["degraded"] is False
    assert retrieval.calls[0]["filters"] == {"repo": "elastic/docs-content", "content_type": "guide"}
    assert retrieval.calls[0]["boosts"] == {"content_type": {"documentation": 0.15}}


def test_search_endpoint_normalizes_extended_metadata_filters() -> None:
    client, retrieval = make_client()

    response = client.post(
        "/api/v1/search",
        json={
            "query": "hybrid retrieval",
            "filters": {
                "repo": " Elastic/Docs-Content ",
                "path": "\\guide\\page.md",
                "heading_path": " Guide > Hybrid ",
                "license_family": " Elastic License ",
            },
        },
    )

    assert response.status_code == 200
    assert retrieval.calls[0]["filters"] == {
        "heading_path": "Guide > Hybrid",
        "license_family": "elastic-license",
        "path": "guide/page.md",
        "repo": "elastic/docs-content",
    }


def test_search_endpoint_explain_mode_returns_score_breakdown() -> None:
    client, _ = make_client()

    response = client.post(
        "/api/v1/search",
        json={"query": "hybrid retrieval", "limit": 2, "explain": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["hits"][0]["score_breakdown"] == {
        "bm25": 0.42,
        "semantic": 0.61,
        "fusion": 0.53,
        "rerank": 0.88,
        "final_rank": 1,
        "final_score": 0.97,
    }


def test_search_endpoint_returns_degraded_warnings() -> None:
    client, retrieval = make_client()

    async def degraded_retrieve(query: str, limit: int = 10, filters: dict | None = None, boosts: dict | None = None):
        result = await FakeRetrievalService().retrieve(query, limit, filters, boosts)
        result["warnings"] = [
            RetrievalWarning(
                code="reranker_unavailable",
                message="Reranker unavailable; ranking uses hybrid fusion.",
                stage="reranking",
            )
        ]
        result["degraded"] = True
        return result

    retrieval.retrieve = degraded_retrieve  # type: ignore[method-assign]

    response = client.post("/api/v1/search", json={"query": "hybrid retrieval"})

    assert response.status_code == 200
    body = response.json()
    assert body["degraded"] is True
    assert body["warnings"] == [
        {
            "code": "reranker_unavailable",
            "message": "Reranker unavailable; ranking uses hybrid fusion.",
            "stage": "reranking",
        }
    ]


def test_answer_endpoint_returns_structured_grounded_evidence() -> None:
    client, _ = make_client()

    response = client.post("/api/v1/answer", json={"query": "best retrieval improvement"})

    assert response.status_code == 200
    body = response.json()
    assert "answer" not in body
    assert "sources" not in body
    assert "Combine lexical and dense retrieval" in body["summary"]
    assert body["direct_answer"] == body["summary"]
    assert body["confidence"] == "high"
    assert body["best_source"]["url"] == "https://www.elastic.co/docs/guide/page#combine"
    assert body["important"]
    assert body["evidence"][0] | {
        "title": "Hybrid search notebook",
        "heading_path": "Guide > Hybrid",
        "repo": "elastic/docs-content",
        "path": "guide/page.md",
        "content_type": "guide",
        "license_family": "elastic-license",
        "score": 0.97,
        "role": "primary",
        "claim": "Combine lexical and dense retrieval, then rerank the merged candidate set before presenting evidence.",
        "excerpt": "Combine lexical and dense retrieval, then rerank the merged candidate set before presenting evidence.",
        "highlight_terms": ["retrieval"],
        "reader_url": "https://www.elastic.co/docs/guide/page#combine",
        "source_url": "https://example.test/hybrid#combine",
        "link_label": "Read documentation",
    } == body["evidence"][0]
    assert [(link["title"], link["url"], link["link_label"]) for link in body["links"][:2]] == [
        ("Hybrid search notebook", "https://www.elastic.co/docs/guide/page#combine", "Read documentation"),
        ("Query rules notebook", "https://www.elastic.co/docs/rules/page#rules", "Read documentation"),
    ]


def test_docs_content_reader_url_resolution_from_markdown_path() -> None:
    assert reader_url_for(
        {
            "repo": "elastic/docs-content",
            "path": "solutions/search/ranking/semantic-reranking.mdx",
            "heading_path": "Semantic reranking > Use cases",
        },
        "https://github.com/elastic/docs-content/blob/main/solutions/search/ranking/semantic-reranking.mdx",
    ) == "https://www.elastic.co/docs/solutions/search/ranking/semantic-reranking#use-cases"


def test_answer_evidence_uses_source_url_for_non_docs_repos() -> None:
    evidence = answer_evidence(
        "hybrid retrieval",
        [
            RankedHit(
                id="lab-1",
                score=0.5,
                metadata={
                    "repo": "elastic/elasticsearch-labs",
                    "path": "supporting-blog-content/example/README.md",
                    "title": "Lab example",
                    "heading_path": "Lab example > Hybrid search",
                },
                source_url="https://github.com/elastic/elasticsearch-labs/blob/abc/supporting-blog-content/example/README.md#hybrid-search",
                text="Hybrid retrieval examples combine structured filtering with semantic search for better relevance.",
                lexical_score=0.2,
                dense_score=0.4,
            )
        ],
    )

    assert evidence[0].reader_url == evidence[0].source_url
    assert evidence[0].link_label == "View source"


def test_answer_evidence_prefers_docs_content_and_limits_counts() -> None:
    hits = [
        RankedHit(
            id="lab-1",
            score=0.99,
            metadata={
                "repo": "elastic/elasticsearch-labs",
                "path": "supporting-blog-content/hybrid/README.md",
                "title": "Lab hybrid retrieval example",
                "heading_path": "Lab > Hybrid retrieval",
                "final_rank": 1,
            },
            source_url="https://github.com/elastic/elasticsearch-labs/blob/abc/supporting-blog-content/hybrid/README.md#hybrid-retrieval",
            text="Hybrid retrieval improvements can combine lexical matching, semantic recall, and application-specific examples.",
            lexical_score=0.8,
            dense_score=0.9,
        ),
        RankedHit(
            id="docs-1",
            score=0.88,
            metadata={
                "repo": "elastic/docs-content",
                "path": "solutions/search/ranking.md",
                "title": "Ranking and reranking",
                "heading_path": "Ranking and reranking > Two-stage retrieval pipelines",
                "final_rank": 2,
            },
            source_url="https://github.com/elastic/docs-content/blob/main/solutions/search/ranking.md#two-stage-retrieval-pipelines",
            text="Hybrid retrieval improvements start with a first-stage candidate set and use reranking only on the strongest candidates.",
            lexical_score=0.7,
            dense_score=0.8,
        ),
        RankedHit(
            id="docs-2",
            score=0.82,
            metadata={
                "repo": "elastic/docs-content",
                "path": "solutions/search/vector/knn.md",
                "title": "kNN search in Elasticsearch",
                "heading_path": "kNN search > Combine approximate kNN with other features",
                "final_rank": 3,
            },
            source_url="https://github.com/elastic/docs-content/blob/main/solutions/search/vector/knn.md#combine-approximate-knn-with-other-features",
            text="Hybrid retrieval improvements often combine approximate kNN with filters and keyword queries for better relevance.",
            lexical_score=0.6,
            dense_score=0.75,
        ),
        RankedHit(
            id="docs-3",
            score=0.7,
            metadata={
                "repo": "elastic/docs-content",
                "path": "solutions/search/semantic-search.md",
                "title": "Semantic search",
                "heading_path": "Semantic search > Blogs",
                "final_rank": 4,
            },
            source_url="https://github.com/elastic/docs-content/blob/main/solutions/search/semantic-search.md#blogs",
            text="Semantic search can improve hybrid retrieval by adding dense vector matches to lexical results.",
            lexical_score=0.5,
            dense_score=0.7,
        ),
    ]

    evidence = answer_evidence("hybrid retrieval improvements", hits, limit=3)

    assert len(evidence) == 3
    assert [item.repo for item in evidence] == [
        "elastic/docs-content",
        "elastic/docs-content",
        "elastic/docs-content",
    ]
    assert evidence[0].title == "Ranking and reranking"
    assert evidence[0].reader_url == (
        "https://www.elastic.co/docs/solutions/search/ranking#two-stage-retrieval-pipelines"
    )
    assert [link.url for link in answer_links(evidence, limit=3)] == [
        "https://www.elastic.co/docs/solutions/search/ranking#two-stage-retrieval-pipelines",
        "https://www.elastic.co/docs/solutions/search/vector/knn#combine-approximate-knn-with-other-features",
        "https://www.elastic.co/docs/solutions/search/semantic-search#blogs",
    ]


def test_answer_summary_uses_grounded_evidence_text() -> None:
    evidence = answer_evidence(
        "hybrid retrieval improvements",
        [
            RankedHit(
                id="docs-1",
                score=0.9,
                metadata={
                    "repo": "elastic/docs-content",
                    "path": "solutions/search/ranking.md",
                    "title": "Ranking and reranking",
                    "heading_path": "Ranking and reranking > Two-stage retrieval pipelines",
                    "final_rank": 1,
                },
                source_url="https://github.com/elastic/docs-content/blob/main/solutions/search/ranking.md#two-stage-retrieval-pipelines",
                text="Hybrid retrieval improvements should merge lexical and semantic candidates before reranking the strongest evidence.",
                lexical_score=0.6,
                dense_score=0.7,
            )
        ],
    )

    summary = synthesize_answer("hybrid retrieval improvements", evidence)

    assert "Hybrid retrieval improvements should merge lexical and semantic candidates" in summary
    assert "Ranking and reranking" not in summary


def test_analyze_endpoint_returns_recommendations_with_evidence() -> None:
    client, _ = make_client()

    response = client.post("/api/v1/analyze", json={"query": "mapping for changed-source identifiers"})

    assert response.status_code == 200
    body = response.json()
    assert [item["category"] for item in body["recommendations"]] == [
        "relevance",
        "ingestion",
        "mapping",
        "performance",
        "resiliency",
    ]
    assert body["recommendations"][2]["evidence"][0] == {
        "title": "Hybrid search notebook",
        "url": "https://example.test/hybrid#combine",
    }


def test_ingest_repo_endpoint() -> None:
    client, _ = make_client()

    response = client.post(
        "/api/v1/ingest/repo",
        json={"repo_url": "https://github.com/elastic/docs-content.git", "branch": "main", "force": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["repo_url"] == "https://github.com/elastic/docs-content.git"
    assert body["branch"] == "main"
    assert body["message"] == "Ingested for test."
    assert body["new_chunks"] == 0


def test_structured_validation_error() -> None:
    client, _ = make_client()

    response = client.post("/api/v1/search", json={"query": ""})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_unconfigured_retrieval_returns_structured_error(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("QDRANT_URL", raising=False)
    monkeypatch.delenv("TEI_EMBED_URL", raising=False)
    get_async_engine.cache_clear()
    build_retrieval_service.cache_clear()
    client = TestClient(create_app())

    response = client.post("/api/v1/search", json={"query": "hybrid retrieval"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "retrieval_not_configured"
