from typing import TypedDict

from langgraph.graph import END, StateGraph


class ResearchState(TypedDict):
    query: str
    summary: str


def summarize_seed(state: ResearchState) -> ResearchState:
    query = state.get("query", "music")
    return {"query": query, "summary": f"GrooveGraph is ready to research {query}."}


def build_research_graph():
    graph = StateGraph(ResearchState)
    graph.add_node("summarize_seed", summarize_seed)
    graph.set_entry_point("summarize_seed")
    graph.add_edge("summarize_seed", END)
    return graph.compile()
