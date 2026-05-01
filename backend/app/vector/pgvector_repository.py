from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from backend.app.vector.qdrant_client import SearchHit, VectorPoint


class PgVectorRepository:
    def __init__(self, engine: AsyncEngine, table_name: str = "document_vectors") -> None:
        self.engine = engine
        self.table_name = table_name

    async def upsert(self, points: list[VectorPoint]) -> None:
        if not points:
            return

        async with self.engine.begin() as connection:
            await self.upsert_with_connection(connection, points)

    async def upsert_with_connection(self, connection: AsyncConnection, points: list[VectorPoint]) -> None:
        statement = text(
            f"""
            INSERT INTO {self.table_name} (id, embedding, metadata, source_url)
            VALUES (:id, :embedding, CAST(:metadata AS jsonb), :source_url)
            ON CONFLICT (id) DO UPDATE SET
                embedding = EXCLUDED.embedding,
                metadata = EXCLUDED.metadata,
                source_url = EXCLUDED.source_url
            """
        )
        await connection.execute(
            statement,
            [
                {
                    "id": point.id,
                    "embedding": vector_literal(point.vector),
                    "metadata": json.dumps(point.payload, sort_keys=True),
                    "source_url": point.source_url,
                }
                for point in points
            ],
        )

    async def search(self, vector: list[float], limit: int, filters: dict | None = None) -> list[SearchHit]:
        where, params = pgvector_filter_clause(filters or {})
        params.update({"embedding": vector_literal(vector), "limit": limit})
        statement = text(
            f"""
            SELECT id, 1 - (embedding <=> CAST(:embedding AS vector)) AS score, metadata, source_url
            FROM {self.table_name}
            {where}
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
            """
        )

        async with self.engine.connect() as connection:
            result = await connection.execute(statement, params)

        hits: list[SearchHit] = []
        for row in result.mappings():
            metadata = dict(row["metadata"] or {})
            hits.append(
                SearchHit(
                    id=str(row["id"]),
                    score=float(row["score"]),
                    metadata=metadata,
                    source_url=str(row["source_url"]),
                )
            )
        return hits


def vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in vector) + "]"


def pgvector_filter_clause(filters: dict) -> tuple[str, dict[str, str]]:
    if not filters:
        return "", {}

    clauses: list[str] = []
    params: dict[str, str] = {}
    for index, (key, value) in enumerate(sorted(filters.items())):
        if value is None:
            continue
        key_param = f"filter_key_{index}"
        value_param = f"filter_value_{index}"
        clauses.append(f"metadata ->> :{key_param} = :{value_param}")
        params[key_param] = str(key)
        params[value_param] = str(value)

    return ("WHERE " + " AND ".join(clauses), params) if clauses else ("", params)

