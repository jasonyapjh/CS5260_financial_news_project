"""
Agent 4: EventClusteringAgent
Groups clean articles into event clusters per the data flow spec.

Steps:
  1. Group articles by ticker
  2. Keyword-rule event type classification on headline + snippet
  3. GPT-4o clustering within each ticker group
  4. Select representative article (highest-credibility source per cluster)

Output cluster schema:
  cluster_id              – "{ticker}_c{n:03d}"
  ticker                  – Stock ticker (or "MACRO")
  event_type              – One of the 11 typed event categories
  articles                – List of canonical article dicts
  representative_headline – Headline from the highest-credibility source
  representative_source   – Source name of the representative article
  article_count           – Number of articles in cluster
  sources                 – Deduplicated list of all source names
"""

import re
from utils.llm import call_openai, extract_json
from utils.state import PipelineState


# ── Event type keyword rules (spec Table) ────────────────────────────────────
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
    ("general_news",      []),   # catch-all
]


def _classify_event_type(headline: str, snippet: str) -> str:
    text = (headline + " " + snippet).lower()
    for event_type, keywords in EVENT_TYPE_RULES:
        if any(kw in text for kw in keywords):
            return event_type
    return "general_news"


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


def _select_representative(articles: list[dict]) -> tuple[str, str]:
    """Return (headline, source) for the highest-credibility article in a cluster."""
    best = max(articles, key=lambda a: a.get("credibility", 0.0))
    return best.get("headline", ""), best.get("source", "Unknown")


def _cluster_ticker_articles(
    ticker: str,
    articles: list[dict],
    openai_key: str,
    ticker_cluster_offset: int,
) -> list[dict]:
    """Cluster articles for one ticker and return cluster dicts."""
    if not articles:
        return []

    articles_text = "\n".join(
        f"[{i}] {a['headline']} | {a['snippet'][:120]}"
        for i, a in enumerate(articles)
    )

    try:
        resp = call_openai(CLUSTER_PROMPT.format(ticker=ticker, articles_text=articles_text), openai_key)
        raw_clusters = extract_json(resp)
    except Exception as e:
        print(f"    [Agent 4] GPT-4o clustering failed for {ticker}: {e} — one cluster per article")
        raw_clusters = [
            {"cluster_indices": [i], "event_type": _classify_event_type(a["headline"], a["snippet"])}
            for i, a in enumerate(articles)
        ]

    clusters: list[dict] = []
    for n, rc in enumerate(raw_clusters):
        indices = [idx for idx in rc.get("cluster_indices", []) if 0 <= idx < len(articles)]
        if not indices:
            continue

        cluster_articles = [articles[idx] for idx in indices]
        rep_headline, rep_source = _select_representative(cluster_articles)
        all_sources = list({a["source"] for a in cluster_articles})

        # GPT-4o may return an event_type; cross-check with keyword rules
        gpt_event_type = rc.get("event_type", "general_news")
        kw_event_type  = _classify_event_type(rep_headline, cluster_articles[0].get("snippet", ""))
        # Prefer keyword match (deterministic) unless GPT returned a more specific type
        event_type = gpt_event_type if gpt_event_type != "general_news" else kw_event_type

        clusters.append({
            "cluster_id":             f"{ticker}_c{ticker_cluster_offset + n:03d}",
            "ticker":                 ticker,
            "event_type":             event_type,
            "articles":               cluster_articles,
            "representative_headline": rep_headline,
            "representative_source":  rep_source,
            "article_count":          len(cluster_articles),
            "sources":                all_sources,
        })

    return clusters


def clustering_agent(state: PipelineState) -> PipelineState:
    state["current_step"] = 4
    state["step_logs"].append("[Agent 4] Clustering articles by ticker then by event...")

    articles = state.get("clean_articles", [])
    if not articles:
        state["event_clusters"] = []
        state["step_logs"].append("[Agent 4] ✓ No articles to cluster")
        return state

    # Group by ticker
    by_ticker: dict[str, list[dict]] = {}
    for art in articles:
        by_ticker.setdefault(art.get("ticker", "UNKNOWN"), []).append(art)

    all_clusters: list[dict] = []
    offset = 0
    for ticker, ticker_articles in by_ticker.items():
        clusters = _cluster_ticker_articles(ticker, ticker_articles, state["openai_key"], offset)
        all_clusters.extend(clusters)
        offset += len(clusters)

    state["event_clusters"] = all_clusters
    state["step_logs"].append(
        f"[Agent 4] ✓ Formed {len(all_clusters)} event clusters "
        f"across {len(by_ticker)} tickers"
    )
    return state
