from langgraph.graph import StateGraph, END
from core.state import PipelineState
from .watchlist_agent import watchlist_agent
from .retrieval_agent import retrieval_agent
from .market_data_agent import market_data_agent
from .filter_agent import filter_agent
from .clustering_agent import clustering_agent
from .summarization_agent import summarization_agent
from .ranking_agent import ranking_agent
from .notification_agent import notification_agent
from utils.config_loader import load_config
import os
from agents.watchlist_agent import WatchlistContextAgent
from dotenv import load_dotenv
load_dotenv()
current_dir = os.path.dirname(os.path.abspath(__file__))
print(f"Current directory: {current_dir}")
# 2. Navigate to the project root 
# (Since dashboard.py is in ui/ui_pages/, we go up 2 levels)
project_root = os.path.abspath(os.path.join(current_dir, ".."))
print(f"Root directory: {project_root}")
# 3. Construct the absolute path to the config
config_path = os.path.join(project_root, "config", "config.yaml")
config = load_config(config_path)

# config = load_config('../config/config.yaml')

def watchlist_node(state: PipelineState)-> PipelineState:
    from agents.watchlist_agent import WatchlistContextAgent
    agent = WatchlistContextAgent(config=config)
    return agent.run(state)

def retrieval_node(state: PipelineState) -> PipelineState:
    from agents.retrieval_agent import NewsRetrievalAgent
    agent = NewsRetrievalAgent(config=config)
    return agent.run(state)

def filter_node(state: PipelineState) -> PipelineState:
    from agents.filter_agent import RelevanceFilterAgent
    agent = RelevanceFilterAgent(config=config)
    return agent.run(state)

def clustering_node(state: PipelineState) -> PipelineState:
    from agents.clustering_agent import EventClusteringAgent
    agent = EventClusteringAgent(config=config)
    return agent.run(state)

def ranking_node(state: PipelineState) -> PipelineState:
    from agents.ranking_agent import ImportanceRankingAgent
    agent = ImportanceRankingAgent(config=config)
    return agent.run(state)

def summarization_node(state: PipelineState) -> PipelineState:
    from agents.summarization_agent import ImpactSummarizationAgent
    agent = ImpactSummarizationAgent(config=config)
    return agent.run(state)

def notification_node(state: PipelineState) -> PipelineState:
    from agents.notification_agent import NotificationAgent
    agent = NotificationAgent(config=config)
    return agent.run(state)

def should_continue(state: PipelineState) -> str:
    """Route: abort on error, else continue."""
    return "abort" if state.errors else "continue"

def abort_node(state: PipelineState) -> PipelineState:
    state.step_logs.append(f"[Pipeline] ✗ Aborted: {state.errors}")
    state.ranked_digest = {"high": [], "medium": [], "low": [], "generated_at": "", "html": "", "text": ""}
    return state



def build_graph() -> StateGraph:

    g = StateGraph(PipelineState)

    g.add_node("watchlist", watchlist_node)
    g.add_node("retrieval", retrieval_node)
    # g.add_node("market_context", market_data_agent)  

    g.add_node("filter", filter_node)
    g.add_node("clustering", clustering_node)
    g.add_node("summarization", summarization_node)
    g.add_node("ranking", ranking_node)
    g.add_node("notification", notification_node)
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

    initial_state =  PipelineState()
    initial_state.watchlist = watchlist
    final_state = graph.invoke(initial_state)
    return final_state