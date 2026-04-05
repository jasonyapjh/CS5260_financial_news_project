"""
Pipeline integration for Streamlit
Directly calls the LangGraph pipeline
"""

import sys
import os
from typing import Dict, List, Any, Callable
import time
import json

# Add parent directory to path for imports
sys.path.insert(0, '/home/ubuntu/financial-news-intelligence-web')

from server.langgraph_pipeline.graph import run_pipeline, create_pipeline_graph
from server.langgraph_pipeline.state import create_initial_state

def execute_pipeline(
    tickers: List[str],
    user_id: int,
    llm_provider: str = "openai",
    llm_api_key: str = None,
    progress_callback: Callable = None
) -> Dict[str, Any]:
    """
    Execute the LangGraph pipeline
    
    Args:
        tickers: List of stock tickers
        user_id: User ID for tracking
        llm_provider: LLM provider (openai or gemini)
        llm_api_key: API key for LLM provider
        progress_callback: Callback function for progress updates
    
    Returns:
        Final pipeline state with results
    """
    
    try:
        # Set environment variables for LLM
        if llm_provider == "openai" and llm_api_key:
            os.environ["OPENAI_API_KEY"] = llm_api_key
        elif llm_provider == "gemini" and llm_api_key:
            os.environ["GOOGLE_API_KEY"] = llm_api_key
        
        # Create run ID (timestamp-based)
        run_id = int(time.time())
        
        # Run pipeline
        final_state = run_pipeline(
            tickers=tickers,
            user_id=user_id,
            run_id=run_id,
            llm_provider=llm_provider,
        )
        
        # Extract results
        result = {
            "status": final_state.get("status", "completed"),
            "tickers": tickers,
            "subject": final_state.get("digest_subject", "Financial News Digest"),
            "html_digest": final_state.get("html_digest", ""),
            "plain_text_digest": final_state.get("plain_text_digest", ""),
            "events": [],
            "event_counts": {
                "high": 0,
                "medium": 0,
                "low": 0,
                "total": 0
            },
            "execution_time": sum(final_state.get("agent_timings", {}).values()),
            "agent_timings": final_state.get("agent_timings", {}),
        }
        
        # Process events
        if "ranked_events" in final_state:
            for event in final_state["ranked_events"]:
                importance = event.get("importance", "medium").lower()
                result["event_counts"][importance] += 1
                result["event_counts"]["total"] += 1
                
                result["events"].append({
                    "ticker": event.get("ticker", ""),
                    "event_type": event.get("event_type", ""),
                    "headline": event.get("headline", ""),
                    "tldr": event.get("tldr", ""),
                    "key_bullets": event.get("key_bullets", []),
                    "impact": event.get("impact", ""),
                    "importance": importance,
                    "score": event.get("score", 0),
                    "verification_status": event.get("verification_status", ""),
                    "source_count": event.get("source_count", 0),
                    "sources": event.get("sources", []),
                })
        
        return result
    
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "events": [],
            "event_counts": {"high": 0, "medium": 0, "low": 0, "total": 0}
        }

def get_pipeline_progress(state: Dict[str, Any]) -> tuple:
    """
    Extract progress information from pipeline state
    
    Returns:
        (progress_percentage, current_agent, status)
    """
    progress = state.get("progress", 0)
    current_agent = state.get("current_agent", "")
    status = state.get("status", "running")
    
    return progress, current_agent, status

def format_event_for_display(event: Dict[str, Any]) -> Dict[str, Any]:
    """Format event data for Streamlit display"""
    return {
        "ticker": event.get("ticker", ""),
        "headline": event.get("headline", ""),
        "tldr": event.get("tldr", ""),
        "importance": event.get("importance", "medium").upper(),
        "score": event.get("score", 0),
        "event_type": event.get("event_type", ""),
        "source_count": event.get("source_count", 0),
        "verification_status": event.get("verification_status", ""),
        "key_bullets": event.get("key_bullets", []),
        "impact": event.get("impact", ""),
        "sources": event.get("sources", []),
    }

def get_importance_color(importance: str) -> str:
    """Get color for importance level"""
    importance = importance.lower()
    if importance == "high":
        return "#d62728"  # Red
    elif importance == "medium":
        return "#ff7f0e"  # Orange
    else:
        return "#2ca02c"  # Green

def get_importance_emoji(importance: str) -> str:
    """Get emoji for importance level"""
    importance = importance.lower()
    if importance == "high":
        return "🔴"
    elif importance == "medium":
        return "🟠"
    else:
        return "🟢"
