"""
core/state.py
-------------
PipelineState — shared state object flowing through every LangGraph node.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from dataclasses import asdict
import json
@dataclass
class PipelineState:
    watchlist:        list[str]  = field(default_factory=list)
    query_bundles:    list[dict] = field(default_factory=list)
    raw_articles:     list[dict] = field(default_factory=list)
    raw_article_count: int = 0
    market_context:   list[dict] = field(default_factory=list)
    # Filter Agent and Filter Critic
    cleaned_articles: list[dict] = field(default_factory=list)
    clean_article_count: int = 0
    filter_retry_count: int = 0
    filter_critique: str = ""
    filter_critic_max_retries: int = 2
    filter_pass_threshold: float = 0.55

    event_clusters:   list[dict] = field(default_factory=list)
    event_cards:      list[dict] = field(default_factory=list)
    
    #Ranking Agent
    ranked_digest:    list[dict] = field(default_factory=list)
    ranking_retry_count: int = 0
    ranking_critique: str = ""
    ranking_critic_max_retries: int = 2
    
    email_output:     dict       = field(default_factory=dict)
    errors:           list[str]  = field(default_factory=list)
    skipped_nodes:    list[str]  = field(default_factory=list)
    
    # UI updates
    current_step:     int        = 0
    step_logs: list[str] = field(default_factory=list)
    
    def summary(self) -> str:
        return (
            f"Watchlist       : {self.watchlist}\n"
            f"Query bundles   : {len(self.query_bundles)}\n"
            f"Raw articles    : {len(self.raw_articles)}\n"
            f"Cleaned articles: {len(self.cleaned_articles)}\n"
            f"Event clusters  : {len(self.event_clusters)}\n"
            f"Event cards     : {len(self.event_cards)}\n"
            f"Ranked events   : {len(self.ranked_digest)}\n"
        )
    
    def to_json(self, filepath: str):
        """Serializes the current state to a JSON file."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=4, ensure_ascii=False)

