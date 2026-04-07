"""
agents/summarization_agent.py
------------------------------
Agent 5 — ImpactSummarizationAgent

Converts each event cluster into a structured event card.
Two GPT-4o calls per cluster:
  Call 1 — Summarization  → tldr, key_facts, impact, sentiment
  Call 2 — Verification   → confidence, uncertainty_flags

Injects market_context (price, returns, analyst data) when available.
Falls back to representative_headline when no OpenAI key is present.
"""

from __future__ import annotations

import json
import os
from dotenv import load_dotenv
from core.base_agent import BaseAgent
from utils.llm import call_openai, extract_json
from core.state import PipelineState
load_dotenv()  # Load environment variables from .env file

SUMMARY_PROMPT = """You are a senior buy-side analyst writing investment intelligence.

Event Type: {event_type}
Ticker: {ticker} — {company}

{market_context_section}

Source articles (up to 5):
{articles_text}

Return ONLY JSON:
{{
  "tldr":      "One crisp sentence summarising the event and its core financial significance",
  "key_facts": [
    "Specific quantitative fact 1 (with numbers where available)",
    "Specific quantitative fact 2",
    "Specific quantitative fact 3"
  ],
  "impact":    "2-3 sentences on investment significance — risks, opportunities, price catalysts",
  "sentiment": "bullish|bearish|neutral"
}}"""

VERIFY_PROMPT = """You are a fact-checker for a financial intelligence system.

Event Card to verify:
{card}

Source evidence:
{evidence}

Return ONLY JSON:
{{
  "verified":              true,
  "confidence":            "high|medium|low",
  "confidence_adjustment": "none|downgrade",
  "uncertainty_flags":     ["unsupported claims, or empty list"]
}}"""


class ImpactSummarizationAgent(BaseAgent):
    """
    Agent 5: GPT-4o event summarization + verification pass.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.openai_key = os.getenv("OPENAI_API_KEY")

    def run(self, state: PipelineState) -> PipelineState:
        clusters = state.event_clusters
        self.log_start(f"{len(clusters)} event clusters")
        state.current_step = 5
        state.step_logs.append("[Agent 5] Summarizing event clusters (GPT-4o)...")

        market_context = state.market_context
        cards: list[dict] = []

        for cluster in clusters:
            cards.append(self._process_cluster(cluster, market_context))

        state.event_cards = cards
        high_conf = sum(1 for c in cards if c["confidence"] == "high")
        msg = f"[Agent 5] ✓ Generated {len(cards)} event cards ({high_conf} high-confidence)"
        state.step_logs.append(msg)
        self.log_done(msg)
        return state

    # ── per-cluster processing ────────────────────────────────────────────────
    def _process_cluster(self, cluster: dict, market_context: dict) -> dict:
        arts   = cluster["articles"][:5]
        ticker = cluster["ticker"]

        base = {
            "cluster_id":              cluster["cluster_id"],
            "ticker":                  ticker,
            "event_type":              cluster["event_type"],
            "representative_headline": cluster["representative_headline"],
            "representative_source":   cluster["representative_source"],
            "supporting_sources":      cluster["sources"],
            "source_urls":             [a["url"] for a in arts],
            "article_count":           cluster["article_count"],
        }

        if not self.openai_key:
            return {**base,
                    "tldr": cluster["representative_headline"],
                    "key_facts": [], "impact": "", "sentiment": "neutral",
                    "confidence": "low",
                    "uncertainty_flags": ["No OpenAI key — fallback to representative headline"]}

        # Call 1: Summarization
        try:
            summary = self._summarise(cluster, arts, ticker, market_context)
        except Exception as e:
            self.logger.error(f"Summarization failed for {cluster['cluster_id']}: {e}")
            summary = {"tldr": cluster["representative_headline"],
                       "key_facts": [], "impact": "", "sentiment": "neutral",
                       "uncertainty_flags": [f"Summarization failed: {e}"]}

        # Call 2: Verification
        confidence        = "low"
        uncertainty_flags = list(summary.pop("uncertainty_flags", []))
        try:
            v = self._verify(summary, arts)
            confidence = v.get("confidence", "medium")
            if v.get("confidence_adjustment") == "downgrade":
                confidence = {"high": "medium", "medium": "low"}.get(confidence, "low")
            uncertainty_flags = list(set(uncertainty_flags + v.get("uncertainty_flags", [])))
        except Exception as e:
            self.logger.warning(f"Verification failed: {e}")
            uncertainty_flags.append(f"Verification failed: {e}")

        return {**base, **summary,
                "confidence":       confidence,
                "uncertainty_flags": [f for f in uncertainty_flags if f]}

    def _summarise(self, cluster: dict, arts: list[dict], ticker: str, mctx: dict) -> dict:
        company   = arts[0].get("company", ticker) if arts else ticker
        art_text  = "\n---\n".join(
            f"Source: {a.get('source','')}\n{a.get('headline','')}\n{a.get('snippet','')}"
            for a in arts
        )
        e_type = cluster.get("event_type", "General News")
        if isinstance(e_type, dict):
            display_event_type = e_type.get("general_news", "General News")
        else:
            display_event_type = e_type
        ctx_sec = self._market_context_section(ticker, mctx)
        resp    = call_openai(
            SUMMARY_PROMPT.format(
                event_type=display_event_type,
                ticker=ticker, company=company,
                market_context_section=ctx_sec,
                articles_text=art_text,
            ),
            self.openai_key,
        )
        return extract_json(resp)

    def _verify(self, summary: dict, arts: list[dict]) -> dict:
        evidence = "\n".join(
            f"[{a.get('source','')}] {a.get('headline','')}: {a.get('snippet','')[:150]}"
            for a in arts
        )
        card_json = json.dumps({"tldr": summary.get("tldr"), "key_facts": summary.get("key_facts")})
        resp = call_openai(VERIFY_PROMPT.format(card=card_json, evidence=evidence), self.openai_key)
        return extract_json(resp)

    @staticmethod
    def _market_context_section(ticker: str, mctx: dict) -> str:
        ctx = mctx.get(ticker)
        if not ctx or ctx.get("_error") or not ctx.get("last_price"):
            return ""
        ccy = ctx.get("currency","")
        lines = ["Market Context:"]
        p1d = ctx.get("price_change_1d"); p5d = ctx.get("price_change_5d")
        lines.append(f"  Price: {ccy} {ctx['last_price']:.2f}  (1D: {p1d:+.1f}%,  5D: {p5d:+.1f}%)" if p1d is not None else f"  Price: {ccy} {ctx['last_price']:.2f}")
        if ctx.get("volume_ratio"):
            lines.append(f"  Volume ratio: {ctx['volume_ratio']:.1f}x avg")
        if ctx.get("analyst_rating"):
            tp = f"  Target: {ccy} {ctx['target_price']:.2f}" if ctx.get("target_price") else ""
            lines.append(f"  Analyst: {ctx['analyst_rating']}{tp}")
        if ctx.get("earnings_date"):
            lines.append(f"  Next earnings: {ctx['earnings_date']}")
        return "\n".join(lines)


# ── LangGraph node wrapper ─────────────────────────────────────────────────────
def summarization_agent(state: PipelineState) -> PipelineState:
    agent = ImpactSummarizationAgent({"openai_key": os.getenv("OPENAI_API_KEY")})
    return agent.run(state)