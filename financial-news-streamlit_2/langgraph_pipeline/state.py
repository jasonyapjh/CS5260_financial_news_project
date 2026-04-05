"""
LangGraph State Schema for Financial News Intelligence Pipeline
Defines the shared state that flows through all 7 agents
Follows the detailed data flow specification with proper article, cluster, and event card schemas
"""

from typing import TypedDict, Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Article:
    """
    Normalized article schema from data collection.
    Every article produced by news retrieval has this structure.
    """
    ticker: str                          # SGX ticker (e.g., D05.SI) or MACRO
    company: str                         # Full company name
    headline: str                        # Article title
    snippet: str                         # Short description or article excerpt
    url: str                            # Canonical article URL
    source: str                         # Data source name (e.g., SGX Announcements, Reuters)
    published_at: str                   # ISO 8601 UTC timestamp
    query_type: str                     # company / industry / macro / sentiment
    raw: Dict[str, Any] = field(default_factory=dict)  # Original API/feed response


@dataclass
class EventCluster:
    """
    Event cluster schema - groups related articles describing the same real-world event.
    Output from Agent 4 (EventClusteringAgent).
    """
    cluster_id: str                     # Unique cluster ID (e.g., D05.SI_c000)
    ticker: str                         # SGX ticker
    event_type: str                     # earnings_release, dividend, guidance_update, etc.
    articles: List[Article] = field(default_factory=list)  # Raw articles in cluster
    representative_headline: str = ""   # Headline of highest-tier source article
    representative_source: str = ""     # Source of representative article
    article_count: int = 0              # Number of articles in cluster
    sources: List[str] = field(default_factory=list)  # Unique sources in cluster


@dataclass
class EventCard:
    """
    Event card schema - structured, human-readable summary of an event.
    Output from Agent 5 (ImpactSummarizationAgent) and Agent 6 (ImportanceRankingAgent).
    """
    # Core event information
    cluster_id: str                     # Reference to source cluster
    ticker: str                         # SGX ticker
    event_type: str                     # Event classification
    
    # Summarization (from Agent 5)
    tldr: str                          # One-line summary
    key_facts: List[str] = field(default_factory=list)  # Bullet points of key facts
    impact: str = ""                   # Impact explanation
    confidence: str = "medium"         # high / medium / low
    uncertainty_flags: List[str] = field(default_factory=list)  # Flags for uncertain facts
    
    # Source information
    supporting_sources: List[str] = field(default_factory=list)  # Source names
    source_urls: List[str] = field(default_factory=list)  # Article URLs
    article_count: int = 0             # Number of articles in cluster
    
    # Importance ranking (from Agent 6)
    importance: str = "Medium"         # High / Medium / Low
    importance_score: float = 0.0      # 0-1 score
    rank_overall: int = 0              # Overall rank across all events
    rank_per_ticker: int = 0           # Rank within this ticker
    
    # Scoring signals (from Agent 6)
    scoring_signals: Dict[str, Any] = field(default_factory=dict)  # Detailed scoring breakdown


@dataclass
class MarketContext:
    """
    Quantitative market context per ticker.
    Output from Agent 1b (MarketDataAgent).
    Used by downstream agents for context and scoring.
    """
    ticker: str
    last_price: float
    currency: str
    price_change_1d: float             # % change in last 1 day
    price_change_5d: float             # % change in last 5 days
    volume_ratio: float                # Current volume / average volume
    analyst_rating: str                # Buy / Hold / Sell
    target_price: float
    earnings_date: Optional[str]       # ISO 8601 date
    recent_eps_actual: float
    recent_eps_estimate: float
    fetched_at: str                    # ISO 8601 UTC timestamp


class PipelineState(TypedDict):
    """
    Shared state object that flows through the LangGraph pipeline.
    Each agent reads from and writes to this state.
    """
    # Input parameters
    tickers: List[str]                 # List of SGX tickers to analyze
    user_id: int                       # User ID for storage
    run_id: int                        # Pipeline run ID for tracking
    llm_provider: str                  # openai or gemini
    
    # Agent 1: WatchlistContextAgent
    ticker_metadata: Dict[str, Dict[str, Any]]  # {ticker: {name, sector, ...}}
    
    # Agent 1b: MarketDataAgent
    market_context: Dict[str, MarketContext]  # {ticker: MarketContext}
    
    # Agent 2: NewsRetrievalAgent
    raw_articles: List[Article]        # All collected articles
    articles_by_ticker: Dict[str, List[Article]]  # {ticker: [articles]}
    
    # Agent 3: NoiseFilterAgent
    filtered_articles: List[Article]   # After hard filters and semantic dedup
    deduplication_metadata: Dict[str, Any]  # Dedup statistics
    
    # Agent 4: EventClusteringAgent
    event_clusters: List[EventCluster]  # Grouped articles by event
    clustering_metadata: Dict[str, Any]  # Clustering statistics
    
    # Agent 5: ImpactSummarizationAgent
    event_cards: List[EventCard]       # Events with summaries
    summarization_metadata: Dict[str, Any]  # Summarization statistics
    
    # Agent 6: ImportanceRankingAgent
    ranked_events: List[EventCard]     # Sorted by importance score
    ranking_metadata: Dict[str, Any]   # Ranking statistics
    
    # Agent 7: NotificationAgent
    digest_json: str                   # JSON digest output
    digest_html: str                   # HTML email output
    digest_subject: str                # Email subject
    
    # Metadata & Error Handling
    current_agent: str                 # Current agent name
    progress: int                      # 0-100
    status: str                        # running / completed / failed
    error_message: str                 # Error details if failed
    agent_timings: Dict[str, float]    # Execution time per agent
    started_at: Optional[datetime]     # Pipeline start time
    completed_at: Optional[datetime]   # Pipeline completion time


def create_initial_state(
    tickers: List[str],
    user_id: int,
    run_id: int,
    llm_provider: str = "openai",
) -> PipelineState:
    """
    Initialize the pipeline state with default values.
    
    Args:
        tickers: List of SGX tickers to analyze
        user_id: User ID for storage
        run_id: Pipeline run ID
        llm_provider: LLM provider (openai or gemini)
    
    Returns:
        Initialized PipelineState
    """
    return {
        "tickers": tickers,
        "user_id": user_id,
        "run_id": run_id,
        "llm_provider": llm_provider,
        "ticker_metadata": {},
        "market_context": {},
        "raw_articles": [],
        "articles_by_ticker": {},
        "filtered_articles": [],
        "deduplication_metadata": {},
        "event_clusters": [],
        "clustering_metadata": {},
        "event_cards": [],
        "summarization_metadata": {},
        "ranked_events": [],
        "ranking_metadata": {},
        "digest_json": "",
        "digest_html": "",
        "digest_subject": "",
        "current_agent": "initializing",
        "progress": 0,
        "status": "running",
        "error_message": "",
        "agent_timings": {},
        "started_at": None,
        "completed_at": None,
    }
