import uuid
from collections.abc import Iterator
from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.models import AgentCheckpoint, Session, SessionMessage, ToolCall, User
from app.config import settings
from app.neo4j_graph import Neo4jGraphService
from app.observability import metrics
from app.rag import WeaviateRagStore
from app.recommendation_planner import RecommendationPlannerService
from app.web_research import ResearchPlanner

Intent = Literal[
    "recommend_music",
    "explain_recommendation",
    "band_history",
    "side_projects",
    "lyrics_meaning",
    "concerts",
    "band_connections",
    "playlist_create",
    "general_chat",
]


class ChatMessage(TypedDict):
    role: str
    content: str


class AgentState(TypedDict, total=False):
    user_id: str
    session_id: str
    messages: list[ChatMessage]
    current_entities: list[str]
    retrieval_question: dict[str, Any]
    used_short_term_memory: bool
    tool_calls: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    answer: str
    citations: list[dict[str, Any]]
    intent: Intent
    route_target: str
    session_db_id: str
    planner_candidates: list[dict[str, Any]]
    web_evidence: list[dict[str, Any]]
    run_id: str


KNOWN_BANDS = {
    "radiohead": "Radiohead",
    "pixies": "Pixies",
    "nirvana": "Nirvana",
    "foo fighters": "Foo Fighters",
    "mike patton": "Mike Patton",
}

SIDE_PROJECTS = {
    "Radiohead": ["Atoms for Peace", "The Smile", "EOB", "Philip Selway solo work"],
    "Pixies": ["The Breeders", "Frank Black solo work", "Grand Duchy", "The Martinis"],
}

PERSON_BAND_MEMBERSHIPS = {
    "Mike Patton": ["Faith No More", "Mr. Bungle", "Fantomas", "Tomahawk", "Peeping Tom", "Dead Cross"],
}


def build_agent_graph():
    graph = StateGraph(AgentState)
    graph.add_node("load_session_context", load_session_context)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("rewrite_or_decompose_query", rewrite_or_decompose_query)
    graph.add_node("route", route)
    graph.add_node("spotify_profile_lookup", spotify_profile_lookup)
    graph.add_node("recommendation_planner", recommendation_planner)
    graph.add_node("graph_retrieval", graph_retrieval)
    graph.add_node("web_research", web_research)
    graph.add_node("vector_retrieval", vector_retrieval)
    graph.add_node("evidence_check", evidence_check)
    graph.add_node("answer_synthesis", answer_synthesis)
    graph.add_node("save_memory", save_memory)

    graph.set_entry_point("load_session_context")
    graph.add_edge("load_session_context", "classify_intent")
    graph.add_edge("classify_intent", "rewrite_or_decompose_query")
    graph.add_edge("rewrite_or_decompose_query", "route")
    graph.add_conditional_edges(
        "route",
        route_key,
        {
            "spotify_profile_lookup": "spotify_profile_lookup",
            "recommendation_planner": "recommendation_planner",
            "graph_retrieval": "graph_retrieval",
            "web_research": "web_research",
            "vector_retrieval": "vector_retrieval",
        },
    )
    graph.add_edge("spotify_profile_lookup", "evidence_check")
    graph.add_edge("recommendation_planner", "evidence_check")
    graph.add_edge("graph_retrieval", "evidence_check")
    graph.add_edge("web_research", "evidence_check")
    graph.add_edge("vector_retrieval", "evidence_check")
    graph.add_edge("evidence_check", "answer_synthesis")
    graph.add_edge("answer_synthesis", "save_memory")
    graph.add_edge("save_memory", END)
    return graph.compile()


def load_session_context(state: AgentState) -> AgentState:
    previous_messages = state.get("messages", [])[:-1]
    prior_entities = _extract_entities(previous_messages)
    current_entities = _extract_entities([state["messages"][-1]]) or prior_entities
    return {
        **state,
        "current_entities": current_entities,
        "used_short_term_memory": bool(prior_entities and not _extract_entities([state["messages"][-1]])),
    }


def classify_intent(state: AgentState) -> AgentState:
    text = state["messages"][-1]["content"].lower()
    intent: Intent = "general_chat"
    if (
        "connect" in text
        or "connection" in text
        or "connected" in text
        or "bands with" in text
        or "member of" in text
        or "fronted" in text
        or "singer in" in text
    ):
        intent = "band_connections"
    elif "side project" in text:
        intent = "side_projects"
    elif "recommend" in text:
        intent = "recommend_music"
    elif "why" in text and "recommend" in text:
        intent = "explain_recommendation"
    elif "history" in text or "bio" in text:
        intent = "band_history"
    elif "lyrics" in text or "meaning" in text:
        intent = "lyrics_meaning"
    elif "concert" in text or "tour" in text:
        intent = "concerts"
    elif "playlist" in text:
        intent = "playlist_create"
    return {**state, "intent": intent}


def rewrite_or_decompose_query(state: AgentState) -> AgentState:
    message = state["messages"][-1]["content"]
    entities = state.get("current_entities", [])
    primary_entity = entities[0] if entities else None
    rewritten = message
    if primary_entity and any(pronoun in message.lower() for pronoun in ["they", "them", "their"]):
        rewritten = (
            message.replace("they", primary_entity)
            .replace("They", primary_entity)
            .replace("them", primary_entity)
            .replace("their", f"{primary_entity}'s")
        )

    decomposed = [{"question": rewritten, "entity": primary_entity, "intent": state.get("intent", "general_chat")}]
    if state.get("intent") == "band_connections" and len(entities) >= 2:
        pair = " and ".join(entities[:2])
        decomposed = [
            {
                "task": "member_relationship",
                "question": f"Identify shared members or member relationships connecting {pair}.",
                "entities": entities[:2],
                "intent": "band_connections",
            },
            {
                "task": "timeline",
                "question": f"Build a timeline explaining how {pair} are connected.",
                "entities": entities[:2],
                "intent": "band_connections",
            },
        ]

    retrieval_question = {
        "original": message,
        "rewritten": rewritten,
        "intent": state.get("intent", "general_chat"),
        "entities": entities,
        "decomposed": decomposed,
    }
    return {**state, "retrieval_question": retrieval_question}


def route(state: AgentState) -> AgentState:
    intent = state.get("intent", "general_chat")
    if intent == "recommend_music":
        target = "recommendation_planner"
    elif intent == "playlist_create":
        target = "spotify_profile_lookup"
    elif intent in {"band_history", "side_projects", "band_connections"}:
        target = "graph_retrieval"
    elif intent in {"concerts", "lyrics_meaning"}:
        target = "web_research"
    else:
        target = "vector_retrieval"
    return {**state, "route_target": target}


def route_key(state: AgentState) -> str:
    return state["route_target"]


def spotify_profile_lookup(state: AgentState) -> AgentState:
    return _append_tool_result(state, "spotify_profile_lookup", "Spotify profile context is available for planning.")


def recommendation_planner(state: AgentState) -> AgentState:
    entity = _primary_entity(state)
    candidates = state.get("planner_candidates", [])
    result = f"Planned {len(candidates)} metadata-backed candidates around {entity or 'the listener'}."
    return _append_tool_result(
        {**state, "evidence": [*state.get("evidence", []), *candidates]},
        "recommendation_planner",
        result,
    )


def graph_retrieval(state: AgentState) -> AgentState:
    entity = _primary_entity(state)
    facts = []
    if state.get("intent") == "side_projects" and entity in SIDE_PROJECTS:
        facts = [f"{entity} side projects include {', '.join(SIDE_PROJECTS[entity])}."]
    elif state.get("intent") == "band_connections" and entity in PERSON_BAND_MEMBERSHIPS:
        bands = PERSON_BAND_MEMBERSHIPS[entity]
        claim = f"{entity} is associated with bands and projects including {', '.join(bands)}."
        evidence = {
            "source": "curated_graph_seed",
            "title": f"{entity} band memberships",
            "claim": claim,
            "confidence": 0.82,
        }
        return _append_tool_result({**state, "evidence": [*state.get("evidence", []), evidence]}, "graph_retrieval", claim)
    elif entity:
        facts = [f"{entity} is the active entity for this session-scoped question."]
    else:
        facts = ["No specific band entity was found."]
    return _append_tool_result(state, "graph_retrieval", " ".join(facts))


def web_research(state: AgentState) -> AgentState:
    entity = _primary_entity(state)
    web_evidence = state.get("web_evidence", [])
    if web_evidence:
        return _append_tool_result(
            {**state, "evidence": [*state.get("evidence", []), *web_evidence]},
            "web_research",
            f"Collected {len(web_evidence)} web research evidence items for {entity or 'the query'}.",
        )
    return _append_tool_result(state, "web_research", f"Prepared web research context for {entity or 'the query'}.")


def vector_retrieval(state: AgentState) -> AgentState:
    return _append_tool_result(state, "vector_retrieval", "Retrieved general GrooveGraph knowledge context.")


def evidence_check(state: AgentState) -> AgentState:
    evidence = state.get("evidence", [])
    checked = [{**item, "checked": True} for item in evidence]
    confidence_values = [float(item.get("confidence", 0.75)) for item in checked]
    weak_evidence = bool(checked) and max(confidence_values) < 0.55
    return {**state, "evidence": checked, "weak_evidence": weak_evidence}


def answer_synthesis(state: AgentState) -> AgentState:
    entity = _primary_entity(state)
    intent = state.get("intent", "general_chat")
    strong_items = [
        item for item in state.get("evidence", []) if "confidence" in item and float(item.get("confidence", 0.0)) >= 0.75
    ]
    weak_items = [
        item for item in state.get("evidence", []) if "confidence" in item and float(item.get("confidence", 0.0)) < 0.55
    ]
    if strong_items:
        claims = [
            item.get("claim") or item.get("result") or item.get("reason")
            for item in strong_items
            if item.get("claim") or item.get("result") or item.get("reason")
        ]
        answer = " ".join(claims)
        if weak_items:
            answer = f"{answer} I found weaker claims too, but I am not treating them as established."
    elif state.get("weak_evidence"):
        answer = "I do not have strong enough evidence to support that claim yet."
    elif intent == "side_projects" and entity in SIDE_PROJECTS:
        answer = f"{entity}'s side projects include {', '.join(SIDE_PROJECTS[entity])}."
    elif entity:
        answer = f"I found session-scoped context for {entity}: {state['retrieval_question']['rewritten']}"
    else:
        answer = "I can help with music discovery, band research, and playlist planning."
    citation_items = strong_items or state.get("evidence", [])
    citations = [
        {
            "source": item.get("tool_name") or item.get("source", "metadata"),
            "summary": item.get("claim") or item.get("result") or item.get("reason", ""),
            "url": item.get("url"),
            "title": item.get("title"),
            "confidence": item.get("confidence"),
        }
        for item in citation_items
    ]
    return {**state, "answer": answer, "citations": citations}


def save_memory(state: AgentState) -> AgentState:
    return state


class GrooveGraphAgent:
    def __init__(self, db: DbSession) -> None:
        self.db = db
        self.graph = build_agent_graph()
        self.planner = RecommendationPlannerService()
        self.research_planner = ResearchPlanner()

    def invoke(self, user: User, external_session_id: str, message: str) -> AgentState:
        session = self._get_or_create_session(user, external_session_id)
        prior_messages = self._load_messages(session)
        state: AgentState = {
            "user_id": str(user.id),
            "session_id": external_session_id,
            "session_db_id": str(session.id),
            "run_id": str(uuid.uuid4()),
            "messages": [*prior_messages, {"role": "user", "content": message}],
            "current_entities": [],
            "used_short_term_memory": False,
            "tool_calls": [],
            "evidence": [],
            "answer": "",
            "citations": [],
        }
        if "recommend" in message.lower():
            allow_rediscovery = "rediscover" in message.lower()
            state["planner_candidates"] = [
                candidate.__dict__
                for candidate in self.planner.plan(self.db, user, message, allow_rediscovery=allow_rediscovery)
            ]
        if _needs_web_research(message):
            state["web_evidence"] = self._run_web_research(message, state)
        result = self.graph.invoke(state)
        self._persist_turn(user, session, result)
        return result

    def stream(self, user: User, external_session_id: str, message: str) -> Iterator[dict[str, Any]]:
        session = self._get_or_create_session(user, external_session_id)
        prior_messages = self._load_messages(session)
        state: AgentState = {
            "user_id": str(user.id),
            "session_id": external_session_id,
            "session_db_id": str(session.id),
            "run_id": str(uuid.uuid4()),
            "messages": [*prior_messages, {"role": "user", "content": message}],
            "current_entities": [],
            "used_short_term_memory": False,
            "tool_calls": [],
            "evidence": [],
            "answer": "",
            "citations": [],
        }
        if "recommend" in message.lower():
            allow_rediscovery = "rediscover" in message.lower()
            state["planner_candidates"] = [
                candidate.__dict__
                for candidate in self.planner.plan(self.db, user, message, allow_rediscovery=allow_rediscovery)
            ]
        if _needs_web_research(message):
            state["web_evidence"] = self._run_web_research(message, state)

        final_state: AgentState | None = None
        for event in self.graph.stream(state, stream_mode="updates"):
            node_name, update = next(iter(event.items()))
            yield {"event": "node", "node": node_name, "data": _jsonable(update)}
            final_state = {**(final_state or state), **update}

        if final_state is not None:
            self._persist_turn(user, session, final_state)
            yield {"event": "answer", "data": {"answer": final_state.get("answer", "")}}

    def history(self, user: User, external_session_id: str) -> dict[str, Any]:
        session = self._get_or_create_session(user, external_session_id)
        checkpoint = self.db.scalar(select(AgentCheckpoint).where(AgentCheckpoint.session_id == session.id))
        return {
            "session_id": external_session_id,
            "messages": self._load_messages(session),
            "checkpoint": checkpoint.state if checkpoint else None,
        }

    def _run_web_research(self, message: str, state: AgentState) -> list[dict[str, Any]]:
        configured = bool(settings.tavily_api_key or settings.brave_search_api_key or settings.serpapi_api_key)
        rag_store = WeaviateRagStore() if configured else None
        graph_service = Neo4jGraphService() if configured else None
        try:
            if graph_service:
                graph_service.ensure_schema()
            return self.research_planner.research(
                message,
                state.get("current_entities", []),
                state.get("intent", "general_chat"),
                db=self.db,
                rag_store=rag_store,
                graph_service=graph_service,
            )
        finally:
            if graph_service:
                graph_service.close()

    def _get_or_create_session(self, user: User, external_session_id: str) -> Session:
        session_uuid = _parse_uuid(external_session_id)
        if session_uuid is not None:
            session = self.db.get(Session, session_uuid)
        else:
            session = self.db.scalar(
                select(Session).where(Session.user_id == user.id, Session.title == external_session_id)
            )
        if session is None:
            session = Session(id=session_uuid or uuid.uuid4(), user_id=user.id, title=external_session_id)
            self.db.add(session)
            self.db.flush()
        return session

    def _load_messages(self, session: Session) -> list[ChatMessage]:
        rows = self.db.scalars(
            select(SessionMessage).where(SessionMessage.session_id == session.id).order_by(SessionMessage.created_at)
        )
        return [{"role": row.role, "content": row.content} for row in rows]

    def _persist_turn(self, user: User, session: Session, state: AgentState) -> None:
        last_user_message = state["messages"][-1]["content"]
        self.db.add(SessionMessage(session_id=session.id, role="user", content=last_user_message, message_metadata={}))
        self.db.add(
            SessionMessage(
                session_id=session.id,
                role="assistant",
                content=state.get("answer", ""),
                message_metadata={
                    "intent": state.get("intent"),
                    "retrieval_question": state.get("retrieval_question"),
                    "used_short_term_memory": state.get("used_short_term_memory", False),
                    "current_entities": state.get("current_entities", []),
                },
            )
        )

        for call in state.get("tool_calls", []):
            self.db.add(
                ToolCall(
                    user_id=user.id,
                    session_id=session.id,
                    tool_name=call["tool_name"],
                    arguments=call.get("arguments", {}),
                    result_summary=call.get("result"),
                )
            )

        checkpoint = self.db.scalar(select(AgentCheckpoint).where(AgentCheckpoint.session_id == session.id))
        if checkpoint is None:
            checkpoint = AgentCheckpoint(
                session_id=session.id,
                user_id=user.id,
                external_session_id=state["session_id"],
                state={},
            )
            self.db.add(checkpoint)
        checkpoint.state = _jsonable(state)
        self.db.commit()


def _append_tool_result(state: AgentState, tool_name: str, result: str) -> AgentState:
    retrieval_question = state.get("retrieval_question", {})
    metrics.observe_tool_call(tool_name)
    metrics.observe_retrieval(
        run_id=state.get("run_id"),
        query=retrieval_question.get("original"),
        rewritten_query=retrieval_question.get("rewritten"),
        retriever_used=tool_name,
        top_k=len(state.get("evidence", [])),
        reranker_score=None,
        evidence_quality_score=_evidence_quality(state.get("evidence", [])),
    )
    call = {
        "tool_name": tool_name,
        "run_id": state.get("run_id"),
        "arguments": {
            "retrieval_question": retrieval_question,
            "metrics": {
                "query": retrieval_question.get("original"),
                "rewritten_query": retrieval_question.get("rewritten"),
                "retriever_used": tool_name,
                "top_k": len(state.get("evidence", [])),
                "reranker_score": None,
                "evidence_quality_score": _evidence_quality(state.get("evidence", [])),
            },
        },
        "result": result,
    }
    return {
        **state,
        "tool_calls": [*state.get("tool_calls", []), call],
        "evidence": [*state.get("evidence", []), call],
    }


def _extract_entities(messages: list[ChatMessage]) -> list[str]:
    entities: list[str] = []
    for message in messages:
        text = message["content"].lower()
        for needle, entity in KNOWN_BANDS.items():
            if needle in text and entity not in entities:
                entities.append(entity)
    return entities


def _primary_entity(state: AgentState) -> str | None:
    entities = state.get("current_entities", [])
    return entities[0] if entities else None


def _parse_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


def _needs_web_research(message: str) -> bool:
    text = message.lower()
    return any(
        token in text
        for token in [
            "history",
            "side project",
            "lyrics",
            "meaning",
            "concert",
            "tour",
            "collaboration",
            "connection",
        ]
    )


def _jsonable(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _evidence_quality(evidence: list[dict[str, Any]]) -> float:
    scored = [float(item.get("confidence", 0.0)) for item in evidence if "confidence" in item]
    if not scored:
        return 0.0
    return round(sum(scored) / len(scored), 4)
