"""
LangGraph Pipeline Runner
Standalone script that executes the pipeline and reports progress via JSON
"""

import asyncio
import json
import argparse
import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph_pipeline.graph import run_pipeline, create_initial_state
from langgraph_pipeline.state import PipelineState


def report_progress(state: PipelineState):
    """Report progress as JSON to stdout"""
    progress_data = {
        "type": "progress",
        "current_agent": state.get("current_agent", "Unknown"),
        "progress": state.get("progress", 0),
        "status": state.get("status", "running"),
    }
    print(json.dumps(progress_data))
    sys.stdout.flush()


def report_completion(state: PipelineState):
    """Report completion with results as JSON"""
    # Extract results from state
    results = {
        "type": "complete",
        "status": state.get("status", "completed"),
        "digest_subject": state.get("digest_subject", ""),
        "html_digest": state.get("html_digest", ""),
        "plain_text_digest": state.get("plain_text_digest", ""),
        "tickers": state.get("tickers", []),
        "ranked_events": [
            {
                "headline": event.headline,
                "event_type": event.event_type,
                "tickers": event.tickers,
                "tldr": event.tldr,
                "key_bullets": event.key_bullets,
                "impact_explanation": event.impact_explanation,
                "verification_notes": event.verification_notes,
                "verification_status": event.verification_status,
                "importance": event.importance,
                "score": event.score,
                "source_count": event.source_count,
            }
            for event in state.get("ranked_events", [])
        ],
        "results": {
            "high_priority": sum(
                1 for e in state.get("ranked_events", []) if e.importance == "high"
            ),
            "medium_priority": sum(
                1 for e in state.get("ranked_events", []) if e.importance == "medium"
            ),
            "low_priority": sum(
                1 for e in state.get("ranked_events", []) if e.importance == "low"
            ),
        },
    }
    print(json.dumps(results))
    sys.stdout.flush()


async def main():
    """Main entry point for the pipeline runner"""
    parser = argparse.ArgumentParser(description="LangGraph Financial News Pipeline")
    parser.add_argument("--tickers", type=str, required=True, help="Comma-separated list of tickers")
    parser.add_argument("--user-id", type=int, required=True, help="User ID")
    parser.add_argument("--run-id", type=int, required=True, help="Pipeline run ID")
    parser.add_argument("--llm-provider", type=str, default="openai", help="LLM provider (openai or gemini)")
    parser.add_argument("--llm-key", type=str, help="LLM API key")
    
    args = parser.parse_args()
    
    # Parse tickers
    tickers = [t.strip().upper() for t in args.tickers.split(",")]
    
    # Set environment variables for LLM
    if args.llm_key:
        if args.llm_provider == "gemini":
            os.environ["GOOGLE_API_KEY"] = args.llm_key
        else:
            os.environ["OPENAI_API_KEY"] = args.llm_key
    
    try:
        # Run the pipeline
        final_state = await run_pipeline(
            tickers=tickers,
            user_id=args.user_id,
            run_id=args.run_id,
            llm_provider=args.llm_provider,
            progress_callback=report_progress,
        )
        
        # Report completion
        report_completion(final_state)
        
        # Exit with success
        sys.exit(0)
        
    except Exception as e:
        error_data = {
            "type": "error",
            "error": str(e),
        }
        print(json.dumps(error_data), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
