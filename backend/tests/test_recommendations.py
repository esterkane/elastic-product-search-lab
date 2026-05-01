import httpx
import pytest

from backend.app.embeddings.client import EmbeddingClient
from backend.app.eval.metrics import mrr_at_k, ndcg_at_k, recall_at_k
from backend.app.recommend.service import RecommendationEngine, recommendations_as_dicts
from backend.app.retrieval.service import (
    RankedHit,
    RerankerClient,
    RetrievalService,
    boost_ranked_hits,
    reciprocal_rank_fusion,
)
from backend.app.vector.qdrant_client import SearchHit


class FakeLexicalRepository:
    def __init__(self) -> None:
        self.filters: dict | None = None

    async def search(self, query: str, limit: int, filters: dict | None = None) -> list[RankedHit]:
        self.filters = filters
        return [
            hit("lex-1", 7.0, "Mapping guidance", "mapping"),
            hit("shared", 6.0, "Hybrid search notebook", "relevance"),
        ]


class FakeVectorRepository:
    def __init__(self) -> None:
        self.filters: dict | None = None

    async def upsert(self, points: list) -> None:
        return None

    async def search(self, vector: list[float], limit: int, filters: dict | None = None) -> list[SearchHit]:
        self.filters = filters
        return [
            SearchHit(
                id="shared",
                score=0.91,
                metadata=metadata("Hybrid search notebook", "relevance"),
                source_url="https://example.test/shared",
            ),
            SearchHit(
                id="dense-1",
                score=0.82,
                metadata=metadata("Ingestion guide", "ingestion"),
                source_url="https://example.test/dense-1",
            ),
        ]


def metadata(title: str, content_type: str) -> dict:
    return {
        "repo": "elastic/docs-content",
        "path": "guide/page.md",
        "title": title,
        "heading_path": title,
        "content_type": content_type,
        "license_family": "elastic-license",
    }


def hit(hit_id: str, score: float, title: str, content_type: str) -> RankedHit:
    return RankedHit(
        id=hit_id,
        score=score,
        lexical_score=score,
        metadata=metadata(title, content_type),
        source_url=f"https://example.test/{hit_id}",
        text=title,
    )


def test_reciprocal_rank_fusion_merges_duplicate_candidates() -> None:
    fused = reciprocal_rank_fusion(
        [hit("a", 3.0, "A", "mapping"), hit("b", 2.0, "B", "relevance")],
        [hit("b", 0.9, "B", "relevance"), hit("c", 0.8, "C", "ingestion")],
    )

    assert [candidate.id for candidate in fused] == ["b", "a", "c"]
    assert fused[0].lexical_score == 2.0
    assert fused[0].dense_score == 0.9


def test_metadata_boosts_change_final_fusion_order() -> None:
    boosted = boost_ranked_hits(
        [
            RankedHit(
                id="a",
                score=0.2,
                fusion_score=0.2,
                metadata=metadata("A", "example"),
                source_url="https://example.test/a",
            ),
            RankedHit(
                id="b",
                score=0.19,
                fusion_score=0.19,
                metadata=metadata("B", "documentation"),
                source_url="https://example.test/b",
            ),
        ],
        {"content_type": {"documentation": 0.2}},
    )

    assert [hit.id for hit in boosted] == ["b", "a"]
    assert boosted[0].fusion_score == boosted[0].score


@pytest.mark.anyio
async def test_retrieval_service_embeds_searches_fuses_and_reranks(monkeypatch: pytest.MonkeyPatch) -> None:
    requests: list[dict] = []

    async def fake_post(self: httpx.AsyncClient, url: str, json: dict) -> httpx.Response:
        requests.append({"url": url, "json": json})
        if "embed" in url:
            return httpx.Response(200, json={"embeddings": [[0.1, 0.2]]}, request=httpx.Request("POST", url))
        return httpx.Response(
            200,
            json={"scores": [0.95, 0.1, 0.4]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    lexical_repository = FakeLexicalRepository()
    vector_repository = FakeVectorRepository()
    service = RetrievalService(
        lexical_repository=lexical_repository,
        vector_repository=vector_repository,
        embedding_client=EmbeddingClient("http://tei.local/embed"),
        reranker_client=RerankerClient("http://tei.local/rerank"),
    )
    result = await service.retrieve("changed source identifiers", limit=2)

    hits = result["hits"]
    assert [candidate.id for candidate in hits] == ["shared", "dense-1"]
    assert result["recommendation_categories"] == ["relevance", "ingestion", "mapping", "performance", "resiliency"]
    assert requests[0]["json"] == {"inputs": ["changed source identifiers"]}
    assert requests[1]["json"]["query"] == "changed source identifiers"
    assert lexical_repository.filters == {
        "repo": ["elastic/docs-content", "elastic/elasticsearch-labs", "elastic/labs-releases"]
    }
    assert vector_repository.filters == lexical_repository.filters
    assert hits[0].rerank_score == 0.95
    assert hits[0].metadata["final_rank"] == 1


@pytest.mark.anyio
async def test_retrieval_service_score_breakdown_without_reranker(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_post(self: httpx.AsyncClient, url: str, json: dict) -> httpx.Response:
        return httpx.Response(200, json={"embeddings": [[0.1, 0.2]]}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    service = RetrievalService(
        lexical_repository=FakeLexicalRepository(),
        vector_repository=FakeVectorRepository(),
        embedding_client=EmbeddingClient("http://tei.local/embed"),
    )
    result = await service.retrieve("changed source identifiers", limit=2)

    hits = result["hits"]
    assert hits[0].id == "shared"
    assert hits[0].lexical_score == 6.0
    assert hits[0].dense_score == 0.91
    assert hits[0].fusion_score > 0
    assert hits[0].rerank_score is None
    assert hits[0].score == hits[0].fusion_score
    assert hits[0].metadata["final_rank"] == 1


def test_recommendation_engine_outputs_grounded_category_dicts() -> None:
    recommendations = RecommendationEngine().generate(
        "recent-change queries",
        [
            hit("mapping", 0.99, "Mapping guidance", "mapping"),
            hit("hybrid", 0.88, "Hybrid search notebook", "relevance"),
        ],
    )

    output = recommendations_as_dicts(recommendations)
    assert [item["category"] for item in output] == ["relevance", "ingestion", "mapping", "performance", "resiliency"]
    assert output[2]["category"] == "mapping"
    assert "normalized fields" in str(output[2]["recommendation"])
    assert output[2]["evidence"] == [
        {"title": "Mapping guidance", "source_url": "https://example.test/mapping"},
        {"title": "Hybrid search notebook", "source_url": "https://example.test/hybrid"},
    ]


def test_ranking_metrics() -> None:
    ranked = ["a", "b", "c", "d"]
    relevance = {"b": 3, "d": 1}

    assert round(ndcg_at_k(ranked, relevance, k=10), 4) == 0.6352
    assert mrr_at_k(ranked, {"b", "d"}, k=10) == 0.5
    assert recall_at_k(ranked, {"b", "d", "z"}, k=20) == 2 / 3
