from fastapi.testclient import TestClient

from backend.app.api.admin import get_ingestion_service
from backend.app.dependencies import build_retrieval_service, get_async_engine
from backend.app.api.search import get_retrieval_service
from backend.app.main import create_app
from backend.app.retrieval.service import RankedHit


class FakeRetrievalService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def retrieve(self, query: str, limit: int = 10, filters: dict | None = None) -> dict[str, object]:
        self.calls.append({"query": query, "limit": limit, "filters": filters})
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
                    },
                    source_url="https://example.test/hybrid",
                    text="Combine lexical and dense retrieval.",
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
                    },
                    source_url="https://example.test/rules",
                    text="Use query rules for curated boosts.",
                ),
            ],
            "recommendation_categories": ["relevance", "ingestion", "mapping", "performance", "resiliency"],
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
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["hits"][0]["title"] == "Hybrid search notebook"
    assert body["hits"][0]["source_url"] == "https://example.test/hybrid"
    assert retrieval.calls[0]["filters"] == {"repo": "elastic/docs-content", "content_type": "guide"}


def test_answer_endpoint_returns_source_attributions() -> None:
    client, _ = make_client()

    response = client.post("/api/v1/answer", json={"query": "best retrieval improvement"})

    assert response.status_code == 200
    body = response.json()
    assert "strongest improvement" in body["answer"]
    assert body["sources"] == [
        {"title": "Hybrid search notebook", "url": "https://example.test/hybrid"},
        {"title": "Query rules notebook", "url": "https://example.test/rules"},
    ]


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
        "url": "https://example.test/hybrid",
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
