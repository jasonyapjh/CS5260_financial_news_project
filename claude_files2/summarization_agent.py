"""
Agent 5: ImpactSummarizationAgent
Converts each event cluster into a structured event card with two GPT-4o calls:
  1. Summarization  → tldr, key_facts, impact
  2. Verification   → confidence, uncertainty_flags

Injects market_context (price, analyst rating, volume) when available.

Output event card schema (per spec):
  cluster_id, ticker, event_type,
  tldr, key_facts, impact,
  confidence, uncertainty_flags,
  supporting_sources, source_urls, article_count
"""

import json
from utils.llm import call_openai, extract_json
from utils.state import PipelineState


SUMMARY_PROMPT = """You are a senior buy-side analyst writing investment intelligence for Singapore equity investors.

Event Type: {event_type}
Ticker: {ticker} — {company}

{market_context_section}

Source articles (up to 5):
{articles_text}

Write a structured event card. Return ONLY JSON:
{{
  "tldr":    "One crisp sentence summarising the event and its core financial significance",
  "key_facts": [
    "Specific quantitative fact 1 (with numbers where available)",
    "Specific quantitative fact 2",
    "Specific quantitative fact 3"
  ],
  "impact":  "2-3 sentences on investment significance — risks, opportunities, price catalysts, sector read-through",
  "sentiment": "bullish|bearish|neutral"
}}"""

VERIFY_PROMPT = """You are a fact-checker for a financial intelligence system.

Event Card to verify:
{card}

Source evidence (article headlines and snippets):
{evidence}

Check: Are the tldr and every key_fact directly supported by the source evidence above?
Return ONLY JSON:
{{
  "verified":             true,
  "confidence":           "high|medium|low",
  "confidence_adjustment":"none|downgrade",
  "uncertainty_flags":    ["list any claims not clearly supported by sources, or empty list"]
}}"""


def _build_market_context_section(ticker: str, market_context: dict) -> str:
    """Format market_context for a ticker into a prompt section."""
    ctx = market_context.get(ticker)
    if not ctx:
        return ""
    lines = ["Market Context (for reference):"]
    if ctx.get("last_price"):
        ccy = ctx.get("currency", "")
        p1d = ctx.get("price_change_1d", 0)
        p5d = ctx.get("price_change_5d", 0)
        lines.append(f"  Price: {ccy} {ctx['last_price']:.2f}  (1D: {p1d:+.1f}%,  5D: {p5d:+.1f}%)")
    if ctx.get("volume_ratio"):
        lines.append(f"  Volume ratio vs avg: {ctx['volume_ratio']:.1f}x")
    if ctx.get("analyst_rating"):
        tp = f"  Target: {ctx.get('currency','')} {ctx['target_price']:.2f}" if ctx.get("target_price") else ""
        lines.append(f"  Analyst consensus: {ctx['analyst_rating']}{tp}")
    if ctx.get("recent_eps_actual") is not None:
        lines.append(
            f"  Recent EPS: actual {ctx['recent_eps_actual']}  vs estimate {ctx.get('recent_eps_estimate','?')}"
        )
    if ctx.get("earnings_date"):
        lines.append(f"  Next earnings date: {ctx['earnings_date']}")
    return "\n".join(lines)


def _summarise_cluster(cluster: dict, openai_key: str, market_context: dict) -> dict:
    arts    = cluster.get("articles", [])[:5]   # spec: up to 5 per cluster
    ticker  = cluster.get("ticker", "")
    company = arts[0].get("company", ticker) if arts else ticker

    art_text = "\n---\n".join(
        f"Source: {a.get('source', '')}\nHeadline: {a.get('headline', '')}\n{a.get('snippet', '')}"
        for a in arts
    )
    ctx_section = _build_market_context_section(ticker, market_context)

    resp    = call_openai(
        SUMMARY_PROMPT.format(
            event_type=cluster.get("event_type", "general_news"),
            ticker=ticker,
            company=company,
            market_context_section=ctx_section,
            articles_text=art_text,
        ),
        openai_key,
    )
    return extract_json(resp)


def _verify_card(summary: dict, cluster: dict, openai_key: str) -> dict:
    arts     = cluster.get("articles", [])[:5]
    evidence = "\n".join(
        f"[{a.get('source','')}] {a.get('headline','')}: {a.get('snippet','')[:150]}"
        for a in arts
    )
    card_for_check = json.dumps({
        "tldr":      summary.get("tldr"),
        "key_facts": summary.get("key_facts"),
    })
    resp = call_openai(
        VERIFY_PROMPT.format(card=card_for_check, evidence=evidence),
        openai_key,
    )
    return extract_json(resp)


def summarization_agent(state: PipelineState) -> PipelineState:
    state["current_step"] = 5
    state["step_logs"].append("[Agent 5] Summarizing event clusters (GPT-4o)...")

    market_context = state.get("market_context", {})
    cards: list[dict] = []

    for cluster in state.get("event_clusters", []):
        arts = cluster.get("articles", [])
        ticker = cluster.get("ticker", "")

        # ── Fallback if no OpenAI key ─────────────────────────────────────────
        if not state.get("openai_key"):
            cards.append({
                "cluster_id":              cluster.get("cluster_id"),
                "ticker":                  ticker,
                "event_type":              cluster.get("event_type"),
                "representative_headline": cluster.get("representative_headline", ""),
                "representative_source":   cluster.get("representative_source", ""),
                "tldr":                    cluster.get("representative_headline", ""),
                "key_facts":               [],
                "impact":                  "",
                "sentiment":               "neutral",
                "confidence":              "low",
                "uncertainty_flags":       ["No OpenAI key — fallback to representative headline"],
                "supporting_sources":      cluster.get("sources", []),
                "source_urls":             [a.get("url", "") for a in arts],
                "article_count":           cluster.get("article_count", len(arts)),
            })
            continue

        # ── Call 1: Summarization ─────────────────────────────────────────────
        try:
            summary = _summarise_cluster(cluster, state["openai_key"], market_context)
        except Exception as e:
            summary = {
                "tldr":      cluster.get("representative_headline", ""),
                "key_facts": [],
                "impact":    "",
                "sentiment": "neutral",
                "uncertainty_flags": [f"Summarization failed: {e}"],
            }

        # ── Call 2: Verification ──────────────────────────────────────────────
        confidence        = "low"
        uncertainty_flags = list(summary.get("uncertainty_flags", []))
        try:
            verification = _verify_card(summary, cluster, state["openai_key"])
            confidence   = verification.get("confidence", "medium")
            # Downgrade if verifier says so
            if verification.get("confidence_adjustment") == "downgrade":
                if confidence == "high":
                    confidence = "medium"
                elif confidence == "medium":
                    confidence = "low"
            uncertainty_flags = list(set(
                uncertainty_flags + verification.get("uncertainty_flags", [])
            ))
        except Exception as e:
            uncertainty_flags.append(f"Verification failed: {e}")

        cards.append({
            "cluster_id":              cluster.get("cluster_id"),
            "ticker":                  ticker,
            "event_type":              cluster.get("event_type"),
            "representative_headline": cluster.get("representative_headline", ""),
            "representative_source":   cluster.get("representative_source", ""),
            "tldr":                    summary.get("tldr", ""),
            "key_facts":               summary.get("key_facts", []),
            "impact":                  summary.get("impact", ""),
            "sentiment":               summary.get("sentiment", "neutral"),
            "confidence":              confidence,
            "uncertainty_flags":       [f for f in uncertainty_flags if f],
            "supporting_sources":      cluster.get("sources", []),
            "source_urls":             [a.get("url", "") for a in arts],
            "article_count":           cluster.get("article_count", len(arts)),
        })

    state["event_cards"] = cards
    state["step_logs"].append(
        f"[Agent 5] ✓ Generated {len(cards)} event cards "
        f"({sum(1 for c in cards if c['confidence'] == 'high')} high-confidence)"
    )
    return state
