"""
agents/watchlist_agent.py
-------------------------
Agent 1 — WatchlistContextAgent

Resolves stock tickers to structured query bundles.
Each bundle contains the company name, aliases, industry sector,
and a set of company-specific + industry-level search queries
used by Agent 2 (NewsRetrievalAgent).
"""


from __future__ import annotations
import os
from core.base_agent import BaseAgent
from utils.llm import call_openai, extract_json
from core.state import PipelineState
from dotenv import load_dotenv
load_dotenv()
PROMPT = """Given these stock tickers, create a structured query bundle for each one.

Return a JSON array. Each item must follow this exact schema:
{{
  "ticker":          "AAPL",
  "company_name":    "Apple Inc.",
  "aliases":         ["Apple", "Apple Inc"],
  "industry":        "Consumer Electronics",
  "company_queries": [
    "Apple earnings Q4 2025",
    "Apple iPhone sales",
    "Apple stock news"
  ],
  "industry_queries": [
    "smartphone market trends 2025",
    "consumer electronics industry news"
  ]
}}

Tickers: {tickers}

Respond with ONLY the JSON array — no explanation, no markdown fences."""


class WatchlistContextAgent(BaseAgent):
    """
    Agent 1: Resolves tickers to structured query bundles via GPT-4o.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.openai_key = os.getenv("OPENAI_API_KEY")
        #self.openai_key = config.get("openai_key", "")

    def run(self, state: PipelineState) -> PipelineState:
        tickers = state.watchlist
        self.log_start(f"{len(tickers)} tickers: {tickers}")
        state.current_step = 1
        state.step_logs.append(
            f"[Agent 1] Expanding {len(tickers)} tickers into query bundles..."
        )

        prompt = PROMPT.format(tickers=", ".join(tickers))
        try:
            response = call_openai(prompt, self.openai_key)
            bundles  = extract_json(response)
            state.query_bundles = bundles
            state.step_logs.append(
                f"[Agent 1] ✓ Generated {len(bundles)} query bundles"
            )
            self.log_done(f"{len(bundles)} bundles produced")
        except Exception as e:
            self.logger.error(f"Failed: {e}")
            state.errors.append(f"Agent 1 failed: {e}")
            state.query_bundles = []

        return state


# ── LangGraph node wrapper ─────────────────────────────────────────────────────
def watchlist_agent(state: PipelineState) -> PipelineState:
    agent = WatchlistContextAgent({"openai_key": os.getenv("OPENAI_API_KEY")})
    return agent.run(state)