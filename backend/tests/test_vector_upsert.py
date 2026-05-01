import pytest
import httpx

from backend.app.embeddings.client import EmbeddingClient
from backend.app.vector.pgvector_repository import pgvector_filter_clause, vector_literal
from backend.app.vector.qdrant_client import QdrantVectorRepository, VectorPoint, qdrant_filter, qdrant_point_id, vector_payload


@pytest.mark.anyio
async def test_embedding_client_batches_tei_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    requests: list[dict] = []

    async def fake_post(self: httpx.AsyncClient, url: str, json: dict) -> httpx.Response:
        requests.append({"url": url, "json": json})
        return httpx.Response(
            200,
            json={"embeddings": [[0.1, 0.2], [0.3, 0.4]]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    client = EmbeddingClient("http://tei.local/embed", model="bge-small")
    vectors = await client.embed(["first", "second"])

    assert vectors == [[0.1, 0.2], [0.3, 0.4]]
    assert requests == [{"url": "http://tei.local/embed", "json": {"inputs": ["first", "second"], "model": "bge-small"}}]


@pytest.mark.anyio
async def test_embedding_client_accepts_tei_value_response(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_post(self: httpx.AsyncClient, url: str, json: dict) -> httpx.Response:
        return httpx.Response(
            200,
            json={"value": [[0.1, 0.2]], "Count": 1},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    client = EmbeddingClient("http://tei.local/embed")
    assert await client.embed(["first"]) == [[0.1, 0.2]]


@pytest.mark.anyio
async def test_qdrant_ensure_collection_creates_missing_collection(monkeypatch: pytest.MonkeyPatch) -> None:
    requests: list[dict] = []

    async def fake_get(self: httpx.AsyncClient, url: str) -> httpx.Response:
        requests.append({"method": "GET", "url": url})
        return httpx.Response(404, json={"status": {"error": "not found"}}, request=httpx.Request("GET", url))

    async def fake_put(self: httpx.AsyncClient, url: str, json: dict) -> httpx.Response:
        requests.append({"method": "PUT", "url": url, "json": json})
        return httpx.Response(200, json={"status": "ok"}, request=httpx.Request("PUT", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    monkeypatch.setattr(httpx.AsyncClient, "put", fake_put)

    repository = QdrantVectorRepository("http://qdrant.local", "docs")
    await repository.ensure_collection(384)

    assert requests == [
        {"method": "GET", "url": "http://qdrant.local/collections/docs"},
        {
            "method": "PUT",
            "url": "http://qdrant.local/collections/docs",
            "json": {"vectors": {"size": 384, "distance": "Cosine"}},
        },
    ]


@pytest.mark.anyio
async def test_qdrant_upsert_is_idempotent_and_includes_required_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    requests: list[dict] = []

    async def fake_put(self: httpx.AsyncClient, url: str, json: dict) -> httpx.Response:
        requests.append({"url": url, "json": json})
        return httpx.Response(200, json={"status": "ok"}, request=httpx.Request("PUT", url))

    monkeypatch.setattr(httpx.AsyncClient, "put", fake_put)

    point = VectorPoint(
        id="chunk-1",
        vector=[0.1, 0.2, 0.3],
        payload=vector_payload(
            repo="elastic/docs-content",
            path="guide/page.md",
            title="Guide",
            heading_path="Guide > Install",
            content_type="guide",
            license_family="elastic-license",
            source_url="https://github.com/elastic/docs-content/blob/abc/guide/page.md#install",
        ),
        source_url="https://github.com/elastic/docs-content/blob/abc/guide/page.md#install",
    )
    repository = QdrantVectorRepository("http://qdrant.local", "docs")

    await repository.upsert([point])
    await repository.upsert([point])

    assert len(requests) == 2
    upserted = requests[0]["json"]["points"][0]
    assert upserted["id"] == qdrant_point_id("chunk-1")
    assert upserted["payload"] == {**point.payload, "chunk_id": "chunk-1"}
    assert requests[0]["url"] == "http://qdrant.local/collections/docs/points?wait=true"


@pytest.mark.anyio
async def test_qdrant_search_returns_score_metadata_and_source_url(monkeypatch: pytest.MonkeyPatch) -> None:
    posted: list[dict] = []

    async def fake_post(self: httpx.AsyncClient, url: str, json: dict) -> httpx.Response:
        posted.append({"url": url, "json": json})
        return httpx.Response(
            200,
            json={
                "result": [
                    {
                        "id": "chunk-1",
                        "score": 0.88,
                        "payload": {
                            "repo": "elastic/docs-content",
                            "path": "guide/page.md",
                            "title": "Guide",
                            "heading_path": "Guide",
                            "content_type": "guide",
                            "license_family": "elastic-license",
                            "source_url": "https://example.test/source",
                        },
                    }
                ]
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    repository = QdrantVectorRepository("http://qdrant.local", "docs")
    hits = await repository.search([0.1, 0.2], limit=3, filters={"repo": "elastic/docs-content"})

    assert posted[0]["json"]["filter"] == {"must": [{"key": "repo", "match": {"value": "elastic/docs-content"}}]}
    assert hits[0].score == 0.88
    assert hits[0].metadata["repo"] == "elastic/docs-content"
    assert hits[0].source_url == "https://example.test/source"


def test_pgvector_helpers_are_deterministic() -> None:
    where, params = pgvector_filter_clause({"repo": "elastic/docs-content", "content_type": "guide"})

    assert vector_literal([1, 2.5]) == "[1.0,2.5]"
    assert where == "WHERE metadata ->> :filter_key_0 = :filter_value_0 AND metadata ->> :filter_key_1 = :filter_value_1"
    assert params == {
        "filter_key_0": "content_type",
        "filter_value_0": "guide",
        "filter_key_1": "repo",
        "filter_value_1": "elastic/docs-content",
    }


def test_qdrant_filter_is_deterministic() -> None:
    assert qdrant_filter({"repo": "elastic/docs-content", "content_type": "guide"}) == {
        "must": [
            {"key": "content_type", "match": {"value": "guide"}},
            {"key": "repo", "match": {"value": "elastic/docs-content"}},
        ]
    }
    assert qdrant_filter({"repo": ["elastic/docs-content", "elastic/elasticsearch-labs"]}) == {
        "must": [
            {"key": "repo", "match": {"any": ["elastic/docs-content", "elastic/elasticsearch-labs"]}},
        ]
    }
