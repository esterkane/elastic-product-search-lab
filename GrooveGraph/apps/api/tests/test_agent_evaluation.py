import urllib.request
from urllib.error import URLError

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agent_graph import GrooveGraphAgent, build_agent_graph
from app.external_metadata import NormalizedCandidate
from app.models import Base, SpotifyArtist, User, UserFollowedArtist
from app.recommendation_planner import RecommendationPlannerService


def build_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


@pytest.mark.unit
def test_eval_stateful_memory_isolation_rewrites_followups() -> None:
    db = build_session()
    user = User(email="listener@example.com")
    db.add(user)
    db.commit()

    agent = GrooveGraphAgent(db)
    agent.invoke(user, "session-a", "Tell me about Radiohead.")
    agent.invoke(user, "session-b", "Tell me about Pixies.")

    radiohead = agent.invoke(user, "session-a", "What side projects did they have?")
    pixies = agent.invoke(user, "session-b", "What side projects did they have?")

    assert radiohead["current_entities"] == ["Radiohead"]
    assert pixies["current_entities"] == ["Pixies"]
    assert radiohead["used_short_term_memory"] is True
    assert pixies["used_short_term_memory"] is True
    assert radiohead["retrieval_question"]["rewritten"] == "What side projects did Radiohead have?"
    assert pixies["retrieval_question"]["rewritten"] == "What side projects did Pixies have?"


@pytest.mark.unit
def test_eval_rag_grounding_cites_strong_source_and_marks_weak_claim_uncertain() -> None:
    graph = build_agent_graph()
    state = graph.invoke(
        {
            "user_id": "user-1",
            "session_id": "rag-session",
            "messages": [
                {"role": "user", "content": "Tell me about Radiohead."},
                {"role": "user", "content": "Who from this band had side projects?"},
            ],
            "current_entities": [],
            "used_short_term_memory": False,
            "tool_calls": [],
            "evidence": [
                {
                    "source": "official-interview",
                    "title": "Official interview",
                    "url": "https://example.com/strong",
                    "claim": "Thom Yorke and Jonny Greenwood formed The Smile as a side project.",
                    "confidence": 0.92,
                },
                {
                    "source": "forum",
                    "title": "Unverified forum",
                    "url": "https://example.com/weak",
                    "claim": "Colin Greenwood secretly joined an unrelated supergroup.",
                    "confidence": 0.31,
                },
            ],
            "answer": "",
            "citations": [],
        }
    )

    assert "The Smile" in state["answer"]
    assert "secretly joined" not in state["answer"]
    assert "weaker claims" in state["answer"]
    assert state["citations"] == [
        {
            "source": "official-interview",
            "summary": "Thom Yorke and Jonny Greenwood formed The Smile as a side project.",
            "url": "https://example.com/strong",
            "title": "Official interview",
            "confidence": 0.92,
        }
    ]


@pytest.mark.unit
def test_eval_query_transformation_decomposes_band_connection() -> None:
    graph = build_agent_graph()
    state = graph.invoke(
        {
            "user_id": "user-1",
            "session_id": "connection-session",
            "messages": [{"role": "user", "content": "How are Nirvana and Foo Fighters connected?"}],
            "current_entities": [],
            "used_short_term_memory": False,
            "tool_calls": [],
            "evidence": [],
            "answer": "",
            "citations": [],
        }
    )

    tasks = state["retrieval_question"]["decomposed"]
    assert state["retrieval_question"]["entities"] == ["Nirvana", "Foo Fighters"]
    assert tasks[0]["task"] == "member_relationship"
    assert "member relationships" in tasks[0]["question"]
    assert tasks[1]["task"] == "timeline"
    assert "timeline" in tasks[1]["question"]


class FixedLastFm:
    def artist_get_similar(self, artist: str, limit: int = 20):
        return [
            NormalizedCandidate(
                kind="artist",
                name="Pixies",
                mbid="pixies-mbid",
                confidence=0.9,
                source="lastfm",
                reason=f"Similar to fixed seed {artist}",
                seed_references=[{"kind": "artist", "name": artist}],
            )
        ]

    def track_get_similar(self, artist: str, track: str, limit: int = 20):
        return []


class FixedMusicBrainz:
    def fetch_artist_relationships(self, mbid: str):
        return {"collaborations": [{"name": "Throwing Muses", "mbid": "throwing-muses-mbid"}]}


@pytest.mark.unit
def test_eval_recommendations_are_explainable_with_source_provenance() -> None:
    db = build_session()
    user = User(email="listener@example.com")
    seed = SpotifyArtist(spotify_id="spotify:artist:radiohead", name="Radiohead", genres={})
    db.add_all([user, seed])
    db.flush()
    db.add(UserFollowedArtist(user_id=user.id, artist_id=seed.id))
    db.commit()

    planner = RecommendationPlannerService(lastfm=FixedLastFm(), musicbrainz=FixedMusicBrainz())
    _, candidates = planner.run(db, user, include_concert_boost=False)

    assert candidates
    for candidate in candidates:
        assert candidate.reason
        assert candidate.evidence["source"]
        assert candidate.evidence["source_evidence"]
        assert candidate.evidence["seed_references"]


@pytest.mark.e2e
@pytest.mark.requires_docker
def test_eval_docker_smoke_health_web_and_mocked_chat() -> None:
    try:
        api_health = _json_get("http://api:8000/health")
        web_html = urllib.request.urlopen("http://web:3000", timeout=5).read().decode("utf-8")
        chat = _json_post("http://api:8000/chat", {"session_id": "docker-smoke", "message": "Tell me about Radiohead."})
    except URLError as exc:
        pytest.skip(f"Compose services are not reachable from this test container: {exc}")

    assert api_health["status"] == "ok"
    assert "GrooveGraph" in web_html
    assert chat["session_id"] == "docker-smoke"
    assert "Radiohead" in chat["answer"]


def _json_get(url: str):
    import json

    return json.loads(urllib.request.urlopen(url, timeout=5).read().decode("utf-8"))


def _json_post(url: str, payload: dict):
    import json

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return json.loads(urllib.request.urlopen(request, timeout=5).read().decode("utf-8"))
