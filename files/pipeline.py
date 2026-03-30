"""
FinTel LangGraph Pipeline — v2 (OpenAI + LangGraph)

Graph topology:
  watchlist → market_data → retrieval → filter → clustering
           → summarization → ranking → notification → END

market_data (Agent 1b) runs immediately after watchlist so that
price/volume/analyst context is available to Agents 5 and 6.
"""

from langgraph.graph import StateGraph, END

from utils.state import PipelineState
from agents.watchlist_agent    import watchlist_agent
from agents.market_data_agent  import market_data_agent
from agents.retrieval_agent    import retrieval_agent
from agents.filter_agent       import filter_agent
from agents.clustering_agent   import clustering_agent
from agents.summarization_agent import summarization_agent
from agents.ranking_agent      import ranking_agent
from agents.notification_agent import notification_agent


def should_continue(state: PipelineState) -> str:
    return "abort" if state.get("error") else "continue"


def abort_node(state: PipelineState) -> PipelineState:
    state["step_logs"].append(f"[Pipeline] ✗ Aborted: {state.get('error')}")
    state.setdefault("digest", {"high": [], "medium": [], "low": [],
                                "generated_at": "", "html": "", "text": ""})
    return state


def build_graph() -> StateGraph:
    g = StateGraph(PipelineState)

    # Nodes
    g.add_node("watchlist",     watchlist_agent)
    g.add_node("market_data",   market_data_agent)
    g.add_node("retrieval",     retrieval_agent)
    g.add_node("filter",        filter_agent)
    g.add_node("clustering",    clustering_agent)
    g.add_node("summarization", summarization_agent)
    g.add_node("ranking",       ranking_agent)
    g.add_node("notification",  notification_agent)
    g.add_node("abort",         abort_node)

    g.set_entry_point("watchlist")

    # Edges with abort routing
    for src, dst in [
        ("watchlist",     "market_data"),
        ("market_data",   "retrieval"),
        ("retrieval",     "filter"),
        ("filter",        "clustering"),
        ("clustering",    "summarization"),
        ("summarization", "ranking"),
        ("ranking",       "notification"),
    ]:
        g.add_conditional_edges(src, should_continue, {"continue": dst, "abort": "abort"})

    g.add_edge("notification", END)
    g.add_edge("abort", END)

    return g.compile()


def run_pipeline(
    watchlist:   list[str],
    openai_key:  str,
    newsapi_key: str,
) -> PipelineState:
    graph = build_graph()

    initial: PipelineState = {
        "watchlist":          watchlist,
        "openai_key":         openai_key,
        "newsapi_key":        newsapi_key,
        "query_bundles":      [],
        "market_context":     {},
        "raw_articles":       [],
        "raw_article_count":  0,
        "clean_articles":     [],
        "clean_article_count":0,
        "event_clusters":     [],
        "event_cards":        [],
        "ranked_events":      [],
        "digest":             {},
        "current_step":       0,
        "step_logs":          [],
        "error":              None,
    }

    return graph.invoke(initial)


if __name__ == "__main__":
    import argparse, json, os
    p = argparse.ArgumentParser()
    p.add_argument("--tickers", nargs="+", default=["D05.SI", "O39.SI", "U11.SI"])
    p.add_argument("--output", default="output/result.json")
    args = p.parse_args()

    result = run_pipeline(
        watchlist=args.tickers,
        openai_key=os.environ["OPENAI_API_KEY"],
        newsapi_key=os.environ["NEWSAPI_KEY"],
    )

    print("\n".join(result["step_logs"]))
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        out = {k: v for k, v in result.items() if k not in ("openai_key", "newsapi_key")}
        out["digest"] = {k: v for k, v in result["digest"].items() if k != "html"}
        json.dump(out, f, indent=2, default=str)
    print(f"\nSaved → {args.output}")
