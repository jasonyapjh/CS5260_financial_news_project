"""Agent 1: Watchlist & Context — resolves tickers to query bundles."""
from utils.llm import call_openai, extract_json
from utils.state import PipelineState
import json
PROMPT = """Given these stock tickers, create a query bundle for each.

Return a JSON array. Each item:
{{
  "ticker": "AAPL",
  "company_name": "Apple Inc.",
  "aliases": ["Apple", "Apple Inc"],
  "industry": "Consumer Electronics",
  "company_queries": ["Apple earnings Q4 2025", "Apple iPhone revenue", "Apple stock news"],
  "industry_queries": ["smartphone market trends 2025", "consumer electronics industry"]
}}

Tickers: {tickers}

Respond with ONLY the JSON array."""


def watchlist_agent(state: PipelineState) -> PipelineState:
    tickers = state["watchlist"]
    state["current_step"] = 1
    state["step_logs"].append(f"[Agent 1] Expanding {len(tickers)} tickers into query bundles...")

    prompt = PROMPT.format(tickers=", ".join(tickers))
    try:
        with open("agent_1_output.json", "r") as f:
            bundles = json.load(f)
        #response = call_openai(prompt, state["openai_key"])
        #bundles = extract_json(response)

        # output_path = "agent_1_output.json"
        # with open(output_path, "w") as f:
        #     json.dump(bundles, f, indent=4)

        state["query_bundles"] = bundles
        state["step_logs"].append(f"[Agent 1] ✓ Generated {len(bundles)} query bundles")
    except Exception as e:
        state["error"] = f"Agent 1 failed: {e}"
        state["query_bundles"] = []

    return state

def test_watchlist_agent(state: PipelineState) -> PipelineState:
    tickers = state["watchlist"]
    state["current_step"] = 1
    state["step_logs"].append(f"[Agent 1] Expanding {len(tickers)} tickers into query bundles...")

    prompt = PROMPT.format(tickers=", ".join(tickers))
    try:
        response = call_openai(prompt, state["openai_key"])
        bundles = extract_json(response)
        state["query_bundles"] = bundles
        state["step_logs"].append(f"[Agent 1] ✓ Generated {len(bundles)} query bundles")
    except Exception as e:
        state["error"] = f"Agent 1 failed: {e}"
        state["query_bundles"] = []

    return state
