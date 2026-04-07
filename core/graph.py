"""
core/graph.py
-------------
LangGraph implementation of the 7-agent pipeline.

Each agent becomes a node in a StateGraph. PipelineState is the shared
state that flows through every node.

Conditional edges:
    - After filtering: if 0 articles remain, skip straight to notification
      with an empty digest (avoids crashing downstream agents)

Usage:
    app   = build_graph(config, user_settings)
    state = PipelineState(watchlist=["D05.SI", "SE"])
    result = app.invoke(state)
"""

from __future__ import annotations

from langgraph.graph import StateGraph

from core.state import PipelineState
from utils.logger import get_logger

logger = get_logger("graph")


def build_graph(config: dict, user_settings: dict) -> StateGraph:
    """
    Build and compile the LangGraph pipeline.

    Args:
        config:        Loaded config.yaml dict.
        user_settings: Notification preferences passed to NotificationAgent.

    Returns:
        Compiled LangGraph app ready for .invoke(PipelineState(...)).

    Graph structure:
        watchlist → retrieval → filter →(conditional)→ clustering
                                                     → notification
        clustering → summarization → ranking → notification → END

    TODO: implement each node function and wire up the graph.
    """
    # TODO: instantiate agents
    # TODO: define node functions (each receives and returns PipelineState)
    # TODO: add nodes and edges to StateGraph
    # TODO: add conditional edge after filter node
    # TODO: compile and return graph
    raise NotImplementedError


def run_pipeline(
    watchlist: list[str],
    config: dict,
    user_settings: dict,
) -> PipelineState:
    """
    Convenience wrapper: build graph, run it, return final state.

    Args:
        watchlist:     List of SGX tickers, e.g. ["D05.SI", "SE"]
        config:        Loaded config dict.
        user_settings: Notification preferences.

    Returns:
        Final PipelineState with all artifacts populated.
    """
    # TODO: implement
    raise NotImplementedError
