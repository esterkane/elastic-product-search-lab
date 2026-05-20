import pytest

from app.neo4j_graph import Neo4jGraphService, RelationshipProvenance


@pytest.fixture()
def graph_service():
    service = Neo4jGraphService()
    service.ensure_schema()
    with service.driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    yield service
    with service.driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    service.close()


@pytest.mark.integration
def test_relationship_provenance_is_required_and_persisted(graph_service: Neo4jGraphService) -> None:
    graph_service.upsert_band("radiohead", name="Radiohead")
    graph_service.upsert_project("the-smile", name="The Smile")

    relationship = graph_service.upsert_relationship(
        "Project",
        "the-smile",
        "SIDE_PROJECT_OF",
        "Band",
        "radiohead",
        RelationshipProvenance(
            source_id="source-radiohead-1",
            confidence=0.93,
            evidence_text="The Smile is a project involving Radiohead members Thom Yorke and Jonny Greenwood.",
        ),
    )

    provenance = relationship["relationship"]
    assert provenance["source_id"] == "source-radiohead-1"
    assert provenance["confidence"] == 0.93
    assert provenance["evidence_text"].startswith("The Smile")
    assert provenance["extracted_at"]


@pytest.mark.integration
def test_relationship_provenance_requires_evidence(graph_service: Neo4jGraphService) -> None:
    graph_service.upsert_band("radiohead", name="Radiohead")
    graph_service.upsert_project("the-smile", name="The Smile")

    with pytest.raises(ValueError, match="evidence_text or source_chunk_id"):
        graph_service.upsert_relationship(
            "Project",
            "the-smile",
            "SIDE_PROJECT_OF",
            "Band",
            "radiohead",
            RelationshipProvenance(source_id="bad-source", confidence=0.1),
        )


@pytest.mark.integration
def test_side_project_query(graph_service: Neo4jGraphService) -> None:
    graph_service.upsert_band("pixies", name="Pixies")
    graph_service.upsert_project("the-breeders", name="The Breeders")
    graph_service.upsert_relationship(
        "Project",
        "the-breeders",
        "SIDE_PROJECT_OF",
        "Band",
        "pixies",
        RelationshipProvenance(
            source_id="source-pixies-1",
            confidence=0.9,
            source_chunk_id="chunk-pixies-1",
        ),
    )

    projects = graph_service.find_side_projects("Pixies")

    assert len(projects) == 1
    assert projects[0]["project"]["name"] == "The Breeders"
    assert projects[0]["provenance"]["source_chunk_id"] == "chunk-pixies-1"


@pytest.mark.integration
def test_shortest_path_between_bands(graph_service: Neo4jGraphService) -> None:
    graph_service.upsert_band("radiohead", name="Radiohead")
    graph_service.upsert_band("pixies", name="Pixies")
    graph_service.upsert_person("thom-yorke", name="Thom Yorke")
    graph_service.upsert_relationship(
        "Person",
        "thom-yorke",
        "MEMBER_OF",
        "Band",
        "radiohead",
        RelationshipProvenance(source_id="source-member-1", confidence=0.99, evidence_text="Thom Yorke fronts Radiohead."),
    )
    graph_service.upsert_relationship(
        "Person",
        "thom-yorke",
        "INFLUENCED_BY",
        "Band",
        "pixies",
        RelationshipProvenance(source_id="source-influence-1", confidence=0.78, evidence_text="Thom Yorke cited Pixies as an influence."),
    )

    path = graph_service.find_shortest_path_between_bands("Radiohead", "Pixies")

    assert path is not None
    node_names = [node["name"] for node in path["nodes"]]
    relationship_types = [relationship["type"] for relationship in path["relationships"]]
    assert node_names == ["Radiohead", "Thom Yorke", "Pixies"]
    assert relationship_types == ["MEMBER_OF", "INFLUENCED_BY"]


@pytest.mark.integration
def test_live_event_graph_upsert_with_venue_provenance(graph_service: Neo4jGraphService) -> None:
    graph_service.upsert_artist("artist-pixies", name="Pixies")
    graph_service.upsert_event("event-pixies-berlin", name="Pixies at Columbiahalle")
    graph_service.upsert_venue("venue-columbiahalle", name="Columbiahalle", city="Berlin")
    graph_service.upsert_relationship(
        "Artist",
        "artist-pixies",
        "PERFORMED_AT",
        "Event",
        "event-pixies-berlin",
        RelationshipProvenance(
            source_id="bandsintown:pixies-berlin",
            confidence=0.86,
            evidence_text="Pixies are listed as performing at Columbiahalle.",
        ),
    )
    graph_service.upsert_relationship(
        "Event",
        "event-pixies-berlin",
        "AT_VENUE",
        "Venue",
        "venue-columbiahalle",
        RelationshipProvenance(
            source_id="bandsintown:pixies-berlin",
            confidence=0.86,
            evidence_text="The Pixies event is listed at Columbiahalle.",
        ),
    )

    with graph_service.driver.session() as session:
        record = session.run(
            """
            MATCH (:Artist {id: 'artist-pixies'})-[performed:PERFORMED_AT]->(event:Event)-[at:AT_VENUE]->(venue:Venue)
            RETURN event, venue, performed, at
            """
        ).single()

    assert record is not None
    assert dict(record["event"])["name"] == "Pixies at Columbiahalle"
    assert dict(record["venue"])["city"] == "Berlin"
    assert dict(record["performed"])["source_id"] == "bandsintown:pixies-berlin"
    assert dict(record["at"])["evidence_text"].startswith("The Pixies event")
