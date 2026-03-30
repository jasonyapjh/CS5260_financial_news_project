from typing import TypedDict, Optional


class PipelineState(TypedDict):
    # Inputs
    watchlist: list[str]
    openai_key: str
    #newsapi_key: str

    # Agent 1 output
    query_bundles: list[dict]
 
    # Agent 2 output
    raw_articles: list[dict]
    raw_article_count: int

    # Agent 3 output
    clean_articles: list[dict]
    clean_article_count: int

    # Agent 4 output
    event_clusters: list[dict]

    # Agent 5 output
    event_cards: list[dict]

    # Agent 6 output
    ranked_events: list[dict]

    # Agent 7 output
    digest: dict

    # Progress tracking
    current_step: int
    step_logs: list[str]
    error: Optional[str]