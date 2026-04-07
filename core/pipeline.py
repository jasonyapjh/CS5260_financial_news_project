"""
pipeline.py
-----------
Orchestrates the full agentic workflow end-to-end (sequential version).
Calls each agent in sequence and passes structured artifacts downstream.

Stages:
    1. WatchlistContextAgent   → query_bundles
    2. NewsRetrievalAgent      → raw_articles
    3. NoiseFilterAgent        → cleaned_articles
    4. EventClusteringAgent    → event_clusters
    5. ImpactSummarizationAgent→ event_cards
    6. ImportanceRankingAgent  → ranked_digest
    7. NotificationAgent       → email_output

Usage:
    pipeline = FinancialNewsPipeline(config)
    state = pipeline.run(watchlist=["D05.SI", "SE"], user_settings={...})
"""

from core.state import PipelineState
from utils.logger import get_logger

logger = get_logger(__name__)


class FinancialNewsPipeline:

    def __init__(self, config: dict):
        self.config = config
        # TODO: instantiate all agents
        # self.watchlist_agent    = WatchlistContextAgent(config)
        # self.retrieval_agent    = NewsRetrievalAgent(config)
        # self.filter_agent       = NoiseFilterAgent(config)
        # self.clustering_agent   = EventClusteringAgent(config)
        # self.summarization_agent= ImpactSummarizationAgent(config)
        # self.ranking_agent      = ImportanceRankingAgent(config)
        # self.notification_agent = NotificationAgent(config)

    def run(self, watchlist: list[str], user_settings: dict) -> PipelineState:
        """
        Execute the full pipeline for a given watchlist.

        Args:
            watchlist:     List of SGX tickers, e.g. ["D05.SI", "SE"]
            user_settings: Notification preferences (min_importance, max_events, send_email)

        Returns:
            PipelineState with all intermediate and final artifacts populated.
        """
        # TODO: implement — run each agent in sequence, populate state
        raise NotImplementedError
