from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.agent_graph import GrooveGraphAgent
from app.models import AgentCheckpoint, Base, ToolCall, User


def build_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_follow_up_pronouns_resolve_against_isolated_session_memory() -> None:
    db = build_session()
    user = User(email="listener@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)

    agent = GrooveGraphAgent(db)
    agent.invoke(user, "radiohead-session", "Tell me about Radiohead.")
    agent.invoke(user, "pixies-session", "Tell me about Pixies.")

    radiohead = agent.invoke(user, "radiohead-session", "What side projects did they have?")
    pixies = agent.invoke(user, "pixies-session", "What side projects did they have?")

    assert radiohead["current_entities"] == ["Radiohead"]
    assert pixies["current_entities"] == ["Pixies"]
    assert radiohead["used_short_term_memory"] is True
    assert pixies["used_short_term_memory"] is True
    assert radiohead["retrieval_question"]["rewritten"] == "What side projects did Radiohead have?"
    assert pixies["retrieval_question"]["rewritten"] == "What side projects did Pixies have?"
    assert radiohead["retrieval_question"]["decomposed"][0] == {
        "question": "What side projects did Radiohead have?",
        "entity": "Radiohead",
        "intent": "side_projects",
    }
    assert pixies["retrieval_question"]["decomposed"][0] == {
        "question": "What side projects did Pixies have?",
        "entity": "Pixies",
        "intent": "side_projects",
    }
    assert "The Smile" in radiohead["answer"]
    assert "The Breeders" in pixies["answer"]

    checkpoints = db.scalars(select(AgentCheckpoint)).all()
    tool_calls = db.scalars(select(ToolCall)).all()
    assert len(checkpoints) == 2
    assert len(tool_calls) == 4


def test_person_band_membership_question_routes_to_graph_answer() -> None:
    db = build_session()
    user = User(email="listener@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)

    result = GrooveGraphAgent(db).invoke(user, "patton-session", "what are the bands with mike patton")

    assert result["intent"] == "band_connections"
    assert result["current_entities"] == ["Mike Patton"]
    assert result["retrieval_question"]["rewritten"] == "what are the bands with mike patton"
    assert "Faith No More" in result["answer"]
    assert "Mr. Bungle" in result["answer"]
    assert result["citations"][0]["source"] == "curated_graph_seed"
