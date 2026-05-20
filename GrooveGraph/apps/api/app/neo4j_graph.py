from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from neo4j import Driver, GraphDatabase

from app.config import settings

NodeLabel = Literal["User", "Artist", "Band", "Person", "Track", "Album", "Project", "Event", "Venue", "Source"]
RelationshipType = Literal[
    "SAVED",
    "FOLLOWS",
    "LIKES_FROM_PLAYLIST",
    "BY",
    "APPEARS_ON",
    "MEMBER_OF",
    "FORMER_MEMBER_OF",
    "SIDE_PROJECT_OF",
    "COLLABORATED_WITH",
    "INFLUENCED_BY",
    "RELATED_TO",
    "PERFORMED_AT",
    "AT_VENUE",
    "EVIDENCED_BY",
]

NODE_LABELS: tuple[NodeLabel, ...] = (
    "User",
    "Artist",
    "Band",
    "Person",
    "Track",
    "Album",
    "Project",
    "Event",
    "Venue",
    "Source",
)

RELATIONSHIP_TYPES: tuple[RelationshipType, ...] = (
    "SAVED",
    "FOLLOWS",
    "LIKES_FROM_PLAYLIST",
    "BY",
    "APPEARS_ON",
    "MEMBER_OF",
    "FORMER_MEMBER_OF",
    "SIDE_PROJECT_OF",
    "COLLABORATED_WITH",
    "INFLUENCED_BY",
    "RELATED_TO",
    "PERFORMED_AT",
    "AT_VENUE",
    "EVIDENCED_BY",
)


@dataclass(frozen=True)
class RelationshipProvenance:
    source_id: str
    confidence: float
    evidence_text: str | None = None
    source_chunk_id: str | None = None
    extracted_at: datetime | None = None

    def as_props(self) -> dict[str, Any]:
        if not self.evidence_text and not self.source_chunk_id:
            raise ValueError("Relationship provenance requires evidence_text or source_chunk_id.")
        return {
            "source_id": self.source_id,
            "confidence": self.confidence,
            "evidence_text": self.evidence_text,
            "source_chunk_id": self.source_chunk_id,
            "extracted_at": (self.extracted_at or datetime.now(UTC)).isoformat(),
        }


class Neo4jGraphService:
    def __init__(self, driver: Driver | None = None) -> None:
        self.driver = driver or GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    def close(self) -> None:
        self.driver.close()

    def ensure_schema(self) -> None:
        with self.driver.session() as session:
            for label in NODE_LABELS:
                session.run(
                    f"CREATE CONSTRAINT {label.lower()}_id IF NOT EXISTS "
                    f"FOR (n:{label}) REQUIRE n.id IS UNIQUE"
                )

    def upsert_node(self, label: NodeLabel, node_id: str, **properties: Any) -> dict[str, Any]:
        _validate_label(label)
        with self.driver.session() as session:
            record = session.run(
                f"MERGE (n:{label} {{id: $id}}) SET n += $properties RETURN n",
                id=node_id,
                properties={key: value for key, value in properties.items() if value is not None},
            ).single()
            return dict(record["n"])

    def upsert_artist(self, artist_id: str, **properties: Any) -> dict[str, Any]:
        return self.upsert_node("Artist", artist_id, **properties)

    def upsert_band(self, band_id: str, **properties: Any) -> dict[str, Any]:
        return self.upsert_node("Band", band_id, **properties)

    def upsert_person(self, person_id: str, **properties: Any) -> dict[str, Any]:
        return self.upsert_node("Person", person_id, **properties)

    def upsert_track(self, track_id: str, **properties: Any) -> dict[str, Any]:
        return self.upsert_node("Track", track_id, **properties)

    def upsert_project(self, project_id: str, **properties: Any) -> dict[str, Any]:
        return self.upsert_node("Project", project_id, **properties)

    def upsert_event(self, event_id: str, **properties: Any) -> dict[str, Any]:
        return self.upsert_node("Event", event_id, **properties)

    def upsert_venue(self, venue_id: str, **properties: Any) -> dict[str, Any]:
        return self.upsert_node("Venue", venue_id, **properties)

    def upsert_relationship(
        self,
        from_label: NodeLabel,
        from_id: str,
        relationship_type: RelationshipType,
        to_label: NodeLabel,
        to_id: str,
        provenance: RelationshipProvenance,
        **properties: Any,
    ) -> dict[str, Any]:
        _validate_label(from_label)
        _validate_label(to_label)
        _validate_relationship(relationship_type)
        rel_props = {**properties, **provenance.as_props()}
        with self.driver.session() as session:
            record = session.run(
                f"""
                MATCH (a:{from_label} {{id: $from_id}})
                MATCH (b:{to_label} {{id: $to_id}})
                MERGE (a)-[r:{relationship_type} {{source_id: $source_id}}]->(b)
                SET r += $properties
                RETURN a, r, b
                """,
                from_id=from_id,
                to_id=to_id,
                source_id=rel_props["source_id"],
                properties=rel_props,
            ).single()
            if record is None:
                raise ValueError("Both relationship endpoints must exist before upserting a relationship.")
            return {"from": dict(record["a"]), "relationship": dict(record["r"]), "to": dict(record["b"])}

    def find_artist(self, artist_id: str) -> dict[str, Any] | None:
        with self.driver.session() as session:
            record = session.run(
                """
                MATCH (n)
                WHERE (n:Artist OR n:Band OR n:Person) AND n.id = $artist_id
                OPTIONAL MATCH (n)-[r]-(neighbor)
                RETURN n, collect({type: type(r), node: neighbor{.*}, provenance: properties(r)}) AS relationships
                """,
                artist_id=artist_id,
            ).single()
            if record is None:
                return None
            return {"node": dict(record["n"]), "relationships": record["relationships"]}

    def find_side_projects(self, artist: str) -> list[dict[str, Any]]:
        with self.driver.session() as session:
            records = session.run(
                """
                MATCH (artist)
                WHERE (artist:Artist OR artist:Band OR artist:Person)
                  AND (artist.id = $artist OR toLower(artist.name) = toLower($artist))
                MATCH (project)-[r:SIDE_PROJECT_OF]->(artist)
                RETURN project, r
                ORDER BY coalesce(project.name, project.id)
                """,
                artist=artist,
            )
            return [{"project": dict(record["project"]), "provenance": dict(record["r"])} for record in records]

    def find_shortest_path_between_bands(self, from_band: str, to_band: str) -> dict[str, Any] | None:
        with self.driver.session() as session:
            record = session.run(
                """
                MATCH (from:Band), (to:Band)
                WHERE (from.id = $from_band OR toLower(from.name) = toLower($from_band))
                  AND (to.id = $to_band OR toLower(to.name) = toLower($to_band))
                MATCH path = shortestPath((from)-[*..6]-(to))
                RETURN [node IN nodes(path) | node{.*, labels: labels(node)}] AS nodes,
                       [rel IN relationships(path) | {type: type(rel), properties: properties(rel)}] AS relationships
                """,
                from_band=from_band,
                to_band=to_band,
            ).single()
            if record is None:
                return None
            return {"nodes": record["nodes"], "relationships": record["relationships"]}

    def find_collaborators(self, artist: str) -> list[dict[str, Any]]:
        with self.driver.session() as session:
            records = session.run(
                """
                MATCH (artist)
                WHERE (artist:Artist OR artist:Band OR artist:Person)
                  AND (artist.id = $artist OR toLower(artist.name) = toLower($artist))
                MATCH (artist)-[r:COLLABORATED_WITH]-(collaborator)
                RETURN collaborator, r
                ORDER BY coalesce(collaborator.name, collaborator.id)
                """,
                artist=artist,
            )
            return [{"collaborator": dict(record["collaborator"]), "provenance": dict(record["r"])} for record in records]

    def find_unexplored_neighboring_artists(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        with self.driver.session() as session:
            records = session.run(
                """
                MATCH (u:User {id: $user_id})-[:SAVED|FOLLOWS|LIKES_FROM_PLAYLIST]->(seed)
                MATCH (seed)-[:RELATED_TO|COLLABORATED_WITH|INFLUENCED_BY]-(candidate)
                WHERE (candidate:Artist OR candidate:Band OR candidate:Person)
                  AND NOT (u)-[:SAVED|FOLLOWS|LIKES_FROM_PLAYLIST]->(candidate)
                RETURN candidate, count(*) AS shared_edges
                ORDER BY shared_edges DESC, coalesce(candidate.name, candidate.id)
                LIMIT $limit
                """,
                user_id=user_id,
                limit=limit,
            )
            return [{"artist": dict(record["candidate"]), "shared_edges": record["shared_edges"]} for record in records]


def _validate_label(label: str) -> None:
    if label not in NODE_LABELS:
        raise ValueError(f"Unsupported Neo4j label: {label}")


def _validate_relationship(relationship_type: str) -> None:
    if relationship_type not in RELATIONSHIP_TYPES:
        raise ValueError(f"Unsupported Neo4j relationship type: {relationship_type}")


def seed_graph(service: Neo4jGraphService, statements: Iterable[str]) -> None:
    with service.driver.session() as session:
        for statement in statements:
            session.run(statement)
