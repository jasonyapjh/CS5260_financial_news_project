"""
LangGraph Workflow Definition
Orchestrates the 7-agent pipeline with proper state management and error handling
"""

from langgraph.graph import StateGraph, END
from langgraph.errors import NodeInterrupt

from .state import PipelineState, create_initial_state
from .agents import (
    agent_1_watchlist_context,
    agent_1b_market_data,
    agent_2_news_retrieval,
    agent_3_noise_filtering,
    agent_4_event_clustering,
    agent_5_impact_summarization,
    agent_6_importance_ranking,
    agent_7_notification,
)


def create_pipeline_graph():
    """
    Create the LangGraph workflow for the 7-agent pipeline
    
    Flow:
    Agent 1 -> Agent 2 -> Agent 3 -> Agent 4 -> Agent 5 -> Agent 6 -> Agent 7
    
    Each agent can fail, triggering error handling
    """
    
    # Create the state graph
    workflow = StateGraph(PipelineState)
    
    # Add all agent nodes
    workflow.add_node("agent_1", agent_1_watchlist_context)
    workflow.add_node("agent_1b", agent_1b_market_data)
    workflow.add_node("agent_2", agent_2_news_retrieval)
    workflow.add_node("agent_3", agent_3_noise_filtering)
    workflow.add_node("agent_4", agent_4_event_clustering)
    workflow.add_node("agent_5", agent_5_impact_summarization)
    workflow.add_node("agent_6", agent_6_importance_ranking)
    workflow.add_node("agent_7", agent_7_notification)
    
    # Add error handling node
    workflow.add_node("error_handler", handle_agent_error)
    
    # Define edges with conditional routing
    workflow.add_edge("agent_1", "agent_1b")
    workflow.add_edge("agent_1b", "agent_2")
    workflow.add_edge("agent_2", "agent_3")
    workflow.add_edge("agent_3", "agent_4")
    workflow.add_edge("agent_4", "agent_5")
    workflow.add_edge("agent_5", "agent_6")
    workflow.add_edge("agent_6", "agent_7")
    workflow.add_edge("agent_7", END)
    
    # Set entry point
    workflow.set_entry_point("agent_1")
    
    # Compile the graph
    graph = workflow.compile()
    
    return graph


def handle_agent_error(state: PipelineState) -> PipelineState:
    """
    Error handling node - can implement retry logic or fallbacks
    """
    if state["status"] == "failed":
        # Log error
        print(f"Pipeline failed at {state['current_agent']}: {state['error_message']}")
        
        # Could implement retry logic here
        # For now, just mark as failed and end
        return state
    
    return state


def run_pipeline(
    tickers: list[str],
    user_id: int,
    run_id: int,
    llm_provider: str = "openai",
    progress_callback=None,
) -> PipelineState:
    """
    Execute the pipeline with progress tracking
    
    Args:
        tickers: List of stock tickers to analyze
        user_id: User ID for database storage
        run_id: Pipeline run ID for tracking
        llm_provider: LLM provider (openai or gemini)
        progress_callback: Optional callback for progress updates
    
    Returns:
        Final pipeline state with all results
    """
    
    # Create initial state
    state = create_initial_state(tickers, user_id, run_id, llm_provider)
    
    # Create graph
    graph = create_pipeline_graph()
    
    # Run the graph
    try:
        # Execute the graph synchronously
        final_state = graph.invoke(state)
        state = final_state
    
    except Exception as e:
        state["error_message"] = f"Pipeline execution error: {str(e)}"
        state["status"] = "failed"
    
    return state


def get_pipeline_graph():
    """Get the compiled pipeline graph"""
    return create_pipeline_graph()
