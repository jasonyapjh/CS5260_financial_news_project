"""
Test script for LangGraph pipeline
Verifies that all agents execute correctly and produce expected output
"""

import asyncio
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph_pipeline.graph import create_pipeline_graph, run_pipeline
from langgraph_pipeline.state import create_initial_state


def test_pipeline_execution():
    """Test the full pipeline execution"""
    print("=" * 80)
    print("Testing LangGraph Financial News Intelligence Pipeline")
    print("=" * 80)
    
    # Test parameters
    test_tickers = ["AAPL", "NVDA", "TSLA"]
    test_user_id = 1
    test_run_id = 1
    
    print(f"\nTest Parameters:")
    print(f"  Tickers: {test_tickers}")
    print(f"  User ID: {test_user_id}")
    print(f"  Run ID: {test_run_id}")
    
    try:
        # Run the pipeline
        print("\nExecuting pipeline...")
        final_state = run_pipeline(
            tickers=test_tickers,
            user_id=test_user_id,
            run_id=test_run_id,
            llm_provider="openai",
        )
        
        # Verify results
        print("\n" + "=" * 80)
        print("Pipeline Execution Results")
        print("=" * 80)
        
        print(f"\nStatus: {final_state.get('status')}")
        print(f"Current Agent: {final_state.get('current_agent')}")
        print(f"Progress: {final_state.get('progress')}%")
        
        if final_state.get("error_message"):
            print(f"Error: {final_state.get('error_message')}")
            return False
        
        # Check agent timings
        print("\nAgent Execution Times:")
        for agent, timing in final_state.get("agent_timings", {}).items():
            print(f"  {agent}: {timing:.2f}s")
        
        # Check results
        print(f"\nDigest Subject: {final_state.get('digest_subject')}")
        print(f"Events Generated: {len(final_state.get('ranked_events', []))}")
        
        # Categorize events
        ranked_events = final_state.get("ranked_events", [])
        high_count = sum(1 for e in ranked_events if e.importance == "high")
        medium_count = sum(1 for e in ranked_events if e.importance == "medium")
        low_count = sum(1 for e in ranked_events if e.importance == "low")
        
        print(f"  High Priority: {high_count}")
        print(f"  Medium Priority: {medium_count}")
        print(f"  Low Priority: {low_count}")
        
        # Display sample events
        if ranked_events:
            print("\nSample Events (Top 3):")
            for i, event in enumerate(ranked_events[:3], 1):
                print(f"\n  Event {i}:")
                print(f"    Headline: {event.headline}")
                print(f"    Importance: {event.importance.upper()} ({event.score}/100)")
                print(f"    TLDR: {event.tldr}")
                print(f"    Sources: {event.source_count}")
        
        # Check digest generation
        html_digest = final_state.get("html_digest", "")
        text_digest = final_state.get("plain_text_digest", "")
        
        print(f"\nDigest Generation:")
        print(f"  HTML Digest Size: {len(html_digest)} bytes")
        print(f"  Text Digest Size: {len(text_digest)} bytes")
        
        if not html_digest or not text_digest:
            print("  WARNING: Digest content is empty!")
            return False
        
        print("\n" + "=" * 80)
        print("✓ Pipeline test completed successfully!")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Pipeline test failed with error:")
        print(f"  {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_graph_structure():
    """Test that the graph is properly structured"""
    print("\n" + "=" * 80)
    print("Testing LangGraph Structure")
    print("=" * 80)
    
    try:
        graph = create_pipeline_graph()
        print("\n✓ Graph created successfully")
        
        # Get graph structure
        print(f"\nGraph Nodes: {list(graph.nodes.keys())}")
        
        expected_nodes = [
            "agent_1",
            "agent_2",
            "agent_3",
            "agent_4",
            "agent_5",
            "agent_6",
            "agent_7",
            "error_handler",
        ]
        
        for node in expected_nodes:
            if node in graph.nodes:
                print(f"  ✓ {node}")
            else:
                print(f"  ✗ {node} (MISSING)")
                return False
        
        print("\n✓ Graph structure is valid!")
        return True
        
    except Exception as e:
        print(f"\n✗ Graph structure test failed:")
        print(f"  {type(e).__name__}: {str(e)}")
        return False


def main():
    """Run all tests"""
    print(f"\nTest started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Test graph structure
    structure_ok = test_graph_structure()
    
    # Test pipeline execution
    execution_ok = test_pipeline_execution()
    
    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    print(f"Graph Structure: {'PASS' if structure_ok else 'FAIL'}")
    print(f"Pipeline Execution: {'PASS' if execution_ok else 'FAIL'}")
    print(f"\nOverall: {'ALL TESTS PASSED ✓' if (structure_ok and execution_ok) else 'SOME TESTS FAILED ✗'}")
    print("=" * 80)
    
    return 0 if (structure_ok and execution_ok) else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
