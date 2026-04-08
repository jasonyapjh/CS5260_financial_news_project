"""
agents/clustering_agent.py
--------------------------
Agent 4 — EventClusteringAgent

Groups clean articles into typed event clusters, one group per ticker.
Steps:
  1. Group articles by ticker
  2. Keyword-rule event type classification
  3. GPT-4o clustering within each ticker group
  4. Select representative article (highest-credibility source)
"""

from __future__ import annotations

from core.base_agent import BaseAgent
from utils.llm import call_openai, extract_json
from core.state import PipelineState
import os
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

EVENT_TYPE_RULES: list[tuple[str, list[str]]] = [
    ("earnings_release",  ["earnings", "profit", "revenue", "net income", "eps", "quarterly results", "full-year"]),
    ("dividend",          ["dividend", "distribution", "payout", "dpu"]),
    ("guidance_update",   ["guidance", "outlook", "forecast", "profit warning", "upgrade", "downgrade"]),
    ("ma_announcement",   ["acqui", "merger", "takeover", "buyout", " deal", "bid", "offer", "divest"]),
    ("regulatory_action", ["mas ", "regulation", "compliance", "enforcement", "licence", "fine", "penalty"]),
    ("capital_action",    ["rights issue", "placement", "buyback", "bond issue", "capital raise"]),
    ("leadership_change", ["ceo", "chairman", "board", "appoint", "resign", "retire", "chief executive"]),
    ("litigation",        ["lawsuit", "court", "arbitration", "investigation", "probe", "charges"]),
    ("product_launch",    ["launch", "new product", "partnership", "contract win", "awarded", "signed"]),
    ("analyst_rating",    ["analyst", "target price", "overweight", "underweight", "buy rating", "sell rating", "hold rating", "initiates"]),
    ("general_news",      []),
]

CLUSTER_PROMPT = """You are a financial analyst. The articles below all relate to ticker {ticker}.
Group them into distinct event clusters — each cluster represents exactly ONE real-world event.

Return ONLY a JSON array. Each item:
{{
  "cluster_indices": [0, 2, 5],
  "event_type": "earnings_release"
}}

Valid event_type values:
earnings_release, dividend, guidance_update, ma_announcement, regulatory_action,
capital_action, leadership_change, litigation, product_launch, analyst_rating, general_news

Articles:
{articles_text}"""


class EventClusteringAgent(BaseAgent):
    """
    Agent 4: Keyword + GPT-4o event clustering per ticker.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.simulation_mode = config.get("simulation_mode", True)

    def run(self, state: PipelineState) -> PipelineState:
        articles = state.cleaned_articles
        self.log_start(f"{len(articles)} clean articles")
        state.current_step = 4
        state.step_logs.append("[Agent 4] Clustering articles by ticker then by event...")

        if self.simulation_mode:
            with open("clustering_test_output.json", "r",  encoding='utf-8') as f:
                data = extract_json(f.read())
                state = PipelineState(**data)
                msg = f"[Agent 4] ✓ Formed {len(state.event_clusters)} event clusters (simulated)"
                state.step_logs.append(msg)
                self.log_done(msg)
                return state

        if not articles:
            state.event_clusters = []
            state.step_logs.append("[Agent 4] ✓ No articles to cluster")
            self.log_done("No articles")
            return state

        by_ticker: dict[str, list[dict]] = {}
        for art in articles:
            by_ticker.setdefault(art.get("ticker", "UNKNOWN"), []).append(art)

        all_clusters: list[dict] = []
        offset = 0
        for ticker, ticker_articles in by_ticker.items():
            clusters = self._cluster_ticker(ticker, ticker_articles, offset)
            all_clusters.extend(clusters)
            offset += len(clusters)

        state.event_clusters = all_clusters
        msg = (
            f"[Agent 4] ✓ Formed {len(all_clusters)} event clusters "
            f"across {len(by_ticker)} tickers"
        )
        state.step_logs.append(msg)
        self.log_done(msg)
        return state

    # ── helpers ───────────────────────────────────────────────────────────────
    def _cluster_ticker(
        self,
        ticker: str,
        articles: list[dict],
        offset: int,
    ) -> list[dict]:
        if not articles:
            return []

        art_text = "\n".join(
            f"[{i}] {a['headline']} | {a.get('snippet','')[:120]}"
            for i, a in enumerate(articles)
        )
        try:
            resp = call_openai(
                CLUSTER_PROMPT.format(ticker=ticker, articles_text=art_text),
                self.openai_key,
            )
            raw_clusters = extract_json(resp)
        except Exception as e:
            self.logger.warning(f"GPT-4o clustering failed for {ticker}: {e} — one per article")
            raw_clusters = [
                {"cluster_indices": [i], "event_type": self._classify(a["headline"], a.get("snippet",""))}
                for i, a in enumerate(articles)
            ]

        clusters: list[dict] = []
        for n, rc in enumerate(raw_clusters):
            indices = [idx for idx in rc.get("cluster_indices", []) if 0 <= idx < len(articles)]
            if not indices:
                continue
            cluster_arts = [articles[idx] for idx in indices]
            rep_headline, rep_source = self._representative(cluster_arts)
            gpt_et = rc.get("event_type", "general_news")
            kw_et  = self._classify(rep_headline, cluster_arts[0].get("snippet",""))
            clusters.append({
                "cluster_id":              f"{ticker}_c{offset + n:03d}",
                "ticker":                  ticker,
                "event_type":              gpt_et if gpt_et != "general_news" else kw_et,
                "articles":                cluster_arts,
                "representative_headline": rep_headline,
                "representative_source":   rep_source,
                "article_count":           len(cluster_arts),
                "sources":                 list({a["source"] for a in cluster_arts}),
            })
        return clusters

    @staticmethod
    def _classify(headline: str, snippet: str) -> str:
        text = (headline + " " + snippet).lower()
        for event_type, keywords in EVENT_TYPE_RULES:
            if any(kw in text for kw in keywords):
                return event_type
        return "general_news"

    @staticmethod
    def _representative(articles: list[dict]) -> tuple[str, str]:
        best = max(articles, key=lambda a: a.get("credibility", 0.0))
        return best.get("headline", ""), best.get("source", "Unknown")


# ── LangGraph node wrapper ─────────────────────────────────────────────────────
def clustering_agent(state: PipelineState) -> PipelineState:
    agent = EventClusteringAgent({"openai_key": os.getenv("OPENAI_API_KEY")})
    return agent.run(state)