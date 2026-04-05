from langgraph.graph import StateGraph, END
from utils.state import PipelineState
from .watchlist_agent import watchlist_agent
from .retrieval_agent import retrieval_agent
from .filter_agent import filter_agent
from .clustering_agent import clustering_agent
from .summarization_agent import summarization_agent
from .ranking_agent import ranking_agent
from .notification_agent import notification_agent

def should_continue(state: PipelineState) -> str:
    """Route: abort on error, else continue."""
    return "abort" if state.get("error") else "continue"


def abort_node(state: PipelineState) -> PipelineState:
    state["step_logs"].append(f"[Pipeline] ✗ Aborted: {state.get('error')}")
    state["digest"] = {"high": [], "medium": [], "low": [], "generated_at": "", "html": "", "text": ""}
    return state

def build_graph() -> StateGraph:
    g = StateGraph(PipelineState)

    g.add_node("watchlist", watchlist_agent)
    g.add_node("retrieval", retrieval_agent)
    g.add_node("filter", filter_agent)
    g.add_node("clustering", clustering_agent)
    g.add_node("summarization", summarization_agent)
    g.add_node("ranking", ranking_agent)
    g.add_node("notification", notification_agent)
    g.add_node("abort", abort_node)
    g.set_entry_point("watchlist")

    for src, dst in [
        ("watchlist",     "retrieval"),
        ("retrieval",     "filter"),
        ("filter",        "clustering"),
        ("clustering",    "summarization"),
        ("summarization", "ranking"),
        ("ranking",       "notification"),
    ]:
        g.add_conditional_edges(
            src,
            should_continue,
            {"continue": dst, "abort": "abort"},
        )
    g.add_edge("notification", END)
    g.add_edge("abort", END)
    # g.set_finish_point("watchlist")

    return g.compile()

def run_pipeline(
    watchlist: list[str],
    openai_key: str,
) -> PipelineState:
    """Run the full LangGraph pipeline and return the final state."""
    graph = build_graph()

    initial_state: PipelineState = {
        "watchlist": watchlist,
        "openai_key": openai_key,
        "query_bundles": [],
        "raw_articles": [],
        "raw_article_count": 0,
        "clean_articles": [],
        "clean_article_count": 0,
        "event_clusters": [],
        "event_cards": [],
        "ranked_events": [],
        "digest": {},
        "current_step": 0,
        "step_logs": [],
        "error": None,
    }

    final_state = graph.invoke(initial_state)
    return final_state