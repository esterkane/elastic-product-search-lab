from datetime import UTC, datetime

from app.agent_graph import answer_synthesis, evidence_check
from app.rag import (
    RagFilters,
    RagSearchRequest,
    WeaviateRagStore,
    build_weaviate_filter,
    chunk_document,
    citation_from_chunk,
    dedupe_chunks,
)
from app.rag import SourceDocumentInput


def test_chunking_carries_parent_document_metadata() -> None:
    document = SourceDocumentInput(
        source_id="src-1",
        url="https://example.com/radiohead",
        title="Radiohead Profile",
        publisher="Example Music",
        artist_names=["Thom Yorke"],
        band_names=["Radiohead"],
        topic="band_history",
        provenance="crawler",
        confidence=0.82,
        text=" ".join(f"word{i}" for i in range(220)),
    )

    chunks = chunk_document(document, max_words=80, overlap=10)

    assert len(chunks) == 3
    assert chunks[0]["source_id"] == "src-1"
    assert chunks[0]["title"] == "Radiohead Profile"
    assert chunks[0]["band_names"] == ["Radiohead"]
    assert chunks[0]["chunk_index"] == 0
    assert chunks[1]["chunk_text"].startswith("word70")


def test_hybrid_search_query_construction_includes_keyword_vector_and_limit() -> None:
    store = WeaviateRagStore(base_url="http://weaviate.test")
    payload = store.build_hybrid_query(RagSearchRequest(query='Radiohead "side projects"', limit=3))

    query = payload["query"]
    assert "SourceChunk" in query
    assert "hybrid:" in query
    assert 'query: "Radiohead \\"side projects\\""' in query
    assert "alpha: 0.5" in query
    assert "limit: 3" in query


def test_metadata_filters_cover_artist_band_topic_date_and_source_type() -> None:
    filters = RagFilters(
        artist="Thom Yorke",
        band="Radiohead",
        topic="side_projects",
        source_type="interview",
        published_after=datetime(2020, 1, 1, tzinfo=UTC),
        published_before=datetime(2024, 1, 1, tzinfo=UTC),
    )

    where = build_weaviate_filter(filters)

    assert where is not None
    assert 'path: ["artist_names"]' in where
    assert "ContainsAny" in where
    assert 'path: ["band_names"]' in where
    assert 'path: ["topic"]' in where
    assert 'valueText: "side_projects"' in where
    assert 'path: ["source_type"]' in where
    assert "GreaterThanEqual" in where
    assert "LessThanEqual" in where


def test_citation_formatting_and_deduplication() -> None:
    chunk = {
        "source_id": "src-1",
        "title": "Pixies Oral History",
        "url": "https://example.com/pixies",
        "publisher": "Example Music",
        "published_at": "2022-02-01T00:00:00+00:00",
        "chunk_index": 4,
        "provenance": "manual-import",
        "confidence": 0.91,
        "chunk_text": "The Breeders formed as an important Pixies-adjacent side project.",
    }

    citation = citation_from_chunk(chunk)
    unique = dedupe_chunks([chunk, {**chunk, "confidence": 0.2}])

    assert citation.model_dump() == {
        "source_id": "src-1",
        "title": "Pixies Oral History",
        "url": "https://example.com/pixies",
        "publisher": "Example Music",
        "published_at": "2022-02-01T00:00:00+00:00",
        "chunk_index": 4,
        "provenance": "manual-import",
        "confidence": 0.91,
        "quote": "The Breeders formed as an important Pixies-adjacent side project.",
    }
    assert len(unique) == 1


def test_answer_synthesis_refuses_unsupported_weak_evidence() -> None:
    state = {
        "intent": "band_history",
        "current_entities": ["Radiohead"],
        "retrieval_question": {"rewritten": "Unsupported claim about Radiohead"},
        "evidence": [{"tool_name": "vector_retrieval", "result": "thin match", "confidence": 0.2}],
    }

    checked = evidence_check(state)
    answer = answer_synthesis(checked)

    assert checked["weak_evidence"] is True
    assert answer["answer"] == "I do not have strong enough evidence to support that claim yet."
