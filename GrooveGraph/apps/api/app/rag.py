import hashlib
import re
from datetime import datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import SourceChunk, SourceDocument


class SourceDocumentInput(BaseModel):
    source_id: str
    url: str | None = None
    title: str
    publisher: str | None = None
    published_at: datetime | None = None
    fetched_at: datetime | None = None
    artist_names: list[str] = Field(default_factory=list)
    band_names: list[str] = Field(default_factory=list)
    topic: str | None = None
    source_type: str = "web"
    provenance: str | None = None
    confidence: float = 0.75
    text: str


class RagFilters(BaseModel):
    artist: str | None = None
    band: str | None = None
    topic: str | None = None
    source_type: str | None = None
    published_after: datetime | None = None
    published_before: datetime | None = None


class RagSearchRequest(BaseModel):
    query: str
    filters: RagFilters = Field(default_factory=RagFilters)
    limit: int = 8


class Citation(BaseModel):
    source_id: str
    title: str
    url: str | None = None
    publisher: str | None = None
    published_at: str | None = None
    chunk_index: int
    provenance: str | None = None
    confidence: float
    quote: str


class Reranker:
    def rerank(self, query: str, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not settings.reranker_api_key:
            return sorted(chunks, key=lambda chunk: chunk.get("confidence", 0), reverse=True)
        return sorted(chunks, key=lambda chunk: (chunk.get("_additional", {}) or {}).get("score", 0), reverse=True)


class WeaviateRagStore:
    collection = "SourceChunk"

    def __init__(self, base_url: str | None = None, http_client: httpx.Client | None = None) -> None:
        self.base_url = (base_url or settings.weaviate_url).rstrip("/")
        self.http = http_client or httpx.Client(timeout=20)

    def ensure_schema(self) -> None:
        response = self.http.get(f"{self.base_url}/v1/schema/{self.collection}")
        if response.status_code == 200:
            return
        self.http.post(f"{self.base_url}/v1/schema", json=source_chunk_schema()).raise_for_status()

    def index_chunks(self, chunks: list[dict[str, Any]]) -> None:
        self.ensure_schema()
        for chunk in chunks:
            object_id = stable_uuid(chunk["source_id"], str(chunk["chunk_index"]), chunk["chunk_text"])
            self.http.put(
                f"{self.base_url}/v1/objects/{self.collection}/{object_id}",
                json={"class": self.collection, "properties": chunk},
            ).raise_for_status()

    def build_hybrid_query(self, request: RagSearchRequest) -> dict[str, Any]:
        where = build_weaviate_filter(request.filters)
        fields = """
          source_id url title publisher published_at fetched_at artist_names band_names topic
          chunk_text chunk_index provenance confidence source_type
          _additional { score }
        """
        arguments = [f'query: "{escape_graphql(request.query)}"', "alpha: 0.5"]
        if where:
            arguments.append(f"where: {where}")
        return {
            "query": "{ Get { "
            f"{self.collection}(hybrid: {{ {', '.join(arguments)} }}, limit: {request.limit}) "
            f"{{ {fields} }} }} }}"
        }

    def search(self, request: RagSearchRequest) -> list[dict[str, Any]]:
        payload = self.build_hybrid_query(request)
        response = self.http.post(f"{self.base_url}/v1/graphql", json=payload)
        response.raise_for_status()
        chunks = response.json().get("data", {}).get("Get", {}).get(self.collection, [])
        return Reranker().rerank(request.query, dedupe_chunks(chunks))


def source_chunk_schema() -> dict[str, Any]:
    text_props = ["source_id", "url", "title", "publisher", "topic", "chunk_text", "provenance", "source_type"]
    date_props = ["published_at", "fetched_at"]
    array_props = ["artist_names", "band_names"]
    props = [{"name": name, "dataType": ["text"]} for name in text_props]
    props += [{"name": name, "dataType": ["date"]} for name in date_props]
    props += [{"name": name, "dataType": ["text[]"]} for name in array_props]
    props += [{"name": "chunk_index", "dataType": ["int"]}, {"name": "confidence", "dataType": ["number"]}]
    return {"class": "SourceChunk", "vectorizer": "none", "properties": props}


def chunk_document(document: SourceDocumentInput, *, max_words: int = 140, overlap: int = 25) -> list[dict[str, Any]]:
    words = re.findall(r"\S+", document.text)
    if not words:
        return []
    chunks: list[dict[str, Any]] = []
    start = 0
    index = 0
    while start < len(words):
        end = min(start + max_words, len(words))
        chunk_text = " ".join(words[start:end])
        chunks.append(
            {
                "source_id": document.source_id,
                "url": document.url,
                "title": document.title,
                "publisher": document.publisher,
                "published_at": iso_or_none(document.published_at),
                "fetched_at": iso_or_none(document.fetched_at),
                "artist_names": document.artist_names,
                "band_names": document.band_names,
                "topic": document.topic,
                "chunk_text": chunk_text,
                "chunk_index": index,
                "provenance": document.provenance,
                "confidence": document.confidence,
                "source_type": document.source_type,
            }
        )
        if end == len(words):
            break
        start = max(end - overlap, start + 1)
        index += 1
    return dedupe_chunks(chunks)


def persist_source_document(db: Session, document: SourceDocumentInput, chunks: list[dict[str, Any]]) -> SourceDocument:
    source = db.scalar(select(SourceDocument).where(SourceDocument.source_id == document.source_id))
    if source is None:
        source = SourceDocument(source_id=document.source_id, title=document.title, source_type=document.source_type)
        db.add(source)
        db.flush()
    source.title = document.title
    source.url = document.url
    source.source_type = document.source_type
    source.source_metadata = document.model_dump(exclude={"text"}, mode="json")
    existing = db.scalars(select(SourceChunk).where(SourceChunk.source_id == source.id)).all()
    for chunk in existing:
        db.delete(chunk)
    db.flush()
    for chunk in chunks:
        db.add(SourceChunk(source_id=source.id, position=chunk["chunk_index"], content=chunk["chunk_text"]))
    db.commit()
    db.refresh(source)
    return source


def build_weaviate_filter(filters: RagFilters) -> str | None:
    operands: list[str] = []
    if filters.artist:
        operands.append(text_array_contains("artist_names", filters.artist))
    if filters.band:
        operands.append(text_array_contains("band_names", filters.band))
    if filters.topic:
        operands.append(text_equal("topic", filters.topic))
    if filters.source_type:
        operands.append(text_equal("source_type", filters.source_type))
    if filters.published_after:
        operands.append(date_compare("published_at", "GreaterThanEqual", filters.published_after))
    if filters.published_before:
        operands.append(date_compare("published_at", "LessThanEqual", filters.published_before))
    if not operands:
        return None
    if len(operands) == 1:
        return operands[0]
    return "{ operator: And, operands: [" + ", ".join(operands) + "] }"


def text_equal(path: str, value: str) -> str:
    return f'{{ path: ["{path}"], operator: Equal, valueText: "{escape_graphql(value)}" }}'


def text_array_contains(path: str, value: str) -> str:
    return f'{{ path: ["{path}"], operator: ContainsAny, valueTextArray: ["{escape_graphql(value)}"] }}'


def date_compare(path: str, operator: str, value: datetime) -> str:
    return f'{{ path: ["{path}"], operator: {operator}, valueDate: "{value.isoformat()}" }}'


def dedupe_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for chunk in chunks:
        normalized = re.sub(r"\W+", " ", chunk.get("chunk_text", "").lower()).strip()
        fingerprint = hashlib.sha256(normalized[:500].encode("utf-8")).hexdigest()
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        unique.append(chunk)
    return unique


def citation_from_chunk(chunk: dict[str, Any]) -> Citation:
    return Citation(
        source_id=chunk["source_id"],
        title=chunk["title"],
        url=chunk.get("url"),
        publisher=chunk.get("publisher"),
        published_at=chunk.get("published_at"),
        chunk_index=chunk["chunk_index"],
        provenance=chunk.get("provenance"),
        confidence=float(chunk.get("confidence", 0)),
        quote=chunk.get("chunk_text", "")[:280],
    )


def stable_uuid(*parts: str) -> str:
    digest = hashlib.md5("|".join(parts).encode("utf-8"), usedforsecurity=False).hexdigest()
    return f"{digest[:8]}-{digest[8:12]}-{digest[12:16]}-{digest[16:20]}-{digest[20:32]}"


def escape_graphql(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def iso_or_none(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
