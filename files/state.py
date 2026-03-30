"""
LangGraph pipeline state.
All agents share and mutate this typed state dict.
Field names and structure match the Pipeline Data Flow specification exactly.
"""

from typing import TypedDict, Optional


class PipelineState(TypedDict):
    # ── Inputs ─────────────────────────────────────────────────────────────────
    watchlist: list[str]        # e.g. ["D05.SI", "O39.SI"]
    openai_key: str
    newsapi_key: str

    # ── Agent 1: WatchlistContextAgent output ──────────────────────────────────
    query_bundles: list[dict]   # [{ticker, company_name, aliases, sector,
                                #   company_queries, industry_queries}, ...]

    # ── Agent 1b: MarketDataAgent output ──────────────────────────────────────
    # Keyed by ticker. Supplementary quantitative context used by Agents 5 & 6.
    # {
    #   "D05.SI": {
    #     last_price, currency, price_change_1d, price_change_5d,
    #     volume_ratio, analyst_rating, target_price,
    #     earnings_date, recent_eps_actual, recent_eps_estimate, fetched_at
    #   }
    # }
    market_context: dict

    # ── Agent 2: NewsRetrievalAgent output ────────────────────────────────────
    # Normalised article schema (one dict per article):
    # {
    #   ticker, company, headline, snippet, url, source,
    #   published_at, query_type, raw
    # }
    raw_articles: list[dict]
    raw_article_count: int

    # ── Agent 3: NoiseFilterAgent output ─────────────────────────────────────
    # Same article schema as raw_articles, deduplicated and filtered.
    clean_articles: list[dict]
    clean_article_count: int

    # ── Agent 4: EventClusteringAgent output ──────────────────────────────────
    # {
    #   cluster_id, ticker, event_type, articles,
    #   representative_headline, representative_source,
    #   article_count, sources
    # }
    event_clusters: list[dict]

    # ── Agent 5: ImpactSummarizationAgent output ──────────────────────────────
    # {
    #   cluster_id, ticker, event_type,
    #   tldr, key_facts, impact,
    #   confidence, uncertainty_flags,
    #   supporting_sources, source_urls, article_count
    # }
    event_cards: list[dict]

    # ── Agent 6: ImportanceRankingAgent output ────────────────────────────────
    # Event cards + added fields:
    # {
    #   importance, importance_score (0-1), rank_overall, rank_per_ticker,
    #   scoring_signals: {
    #     event_type_weight, corroboration_count, corroboration_score,
    #     novelty_score, credibility_score, confidence_adj
    #   }
    # }
    ranked_events: list[dict]

    # ── Agent 7: NotificationAgent output ─────────────────────────────────────
    digest: dict

    # ── Progress tracking ──────────────────────────────────────────────────────
    current_step: int
    step_logs: list[str]
    error: Optional[str]
