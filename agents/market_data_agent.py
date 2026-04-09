"""
market_data_agent.py
--------------------
Agent 1b — Market Data Agent

Fetches quantitative market context for each ticker in the watchlist
using yfinance. Runs in parallel with (or just before) NewsRetrievalAgent.

This agent enriches the pipeline with price momentum, volume signals,
analyst sentiment, and earnings context — data types that pure news
feeds cannot provide.

Data produced per ticker (MarketSnapshot):
    ┌─────────────────────┬─────────────────────────────────────────────┐
    │ Field               │ Signal                                      │
    ├─────────────────────┼─────────────────────────────────────────────┤
    │ price_change_1d     │ Short-term price reaction to news           │
    │ price_change_5d     │ Weekly trend context                        │
    │ volume_ratio        │ Abnormal activity flag (>2x = spike)        │
    │ analyst_rating      │ Consensus recommendation (Buy/Hold/Sell)    │
    │ target_price        │ 12-month analyst consensus target           │
    │ earnings_date       │ Upcoming catalyst date                      │
    │ recent_eps_actual   │ Most recent earnings beat/miss context      │
    │ recent_eps_estimate │                                             │
    └─────────────────────┴─────────────────────────────────────────────┘

Input:  List of tickers, e.g. ["D05.SI", "O39.SI", "SE"]
Output: Dict[ticker -> MarketSnapshot] — consumed downstream by
        ImportanceRankingAgent (volume spike boost) and
        ImpactSummarizationAgent (price context in summaries).

Usage in pipeline (sequential):
    market_context = MarketDataAgent(config).run(watchlist)

Usage in pipeline (LangGraph parallel):
    Runs as a sibling node to NewsRetrievalAgent, results merged
    into PipelineState.market_context before EventClusteringAgent.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from core.state import PipelineState
from utils.llm import call_openai, extract_json
from core.base_agent import BaseAgent
from data.collectors.stock_price_collector import StockPriceCollector, MarketSnapshot


class MarketDataAgent(BaseAgent):
    """
    Agent 1b: fetches market snapshots for every ticker in the watchlist.

    The output dict is keyed by ticker and stored in pipeline state under
    `market_context`. Downstream agents read from this dict to:
      - Boost importance scores for tickers with volume spikes
      - Prepend price context to LLM summarization prompts
      - Flag pre-/post-earnings articles as higher priority
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.collector    = StockPriceCollector(config)
        self.max_workers  = config.get("market_data_max_workers", 6)
        self.volume_spike = config.get("market_data", {}).get("volume_spike_threshold", 2.0)
        self.simulation_mode = config.get("simulation_mode", True)

    def run(self, state: PipelineState) -> PipelineState:
        watchlist = state.watchlist
        self.log_start(
            f"Fetching market data for {len(watchlist)} tickers."
        )

        market_context: dict[str, MarketSnapshot] = {}

        if self.simulation_mode:
            with open("market_data_test_output.json", "r",  encoding='utf-8') as f:
                data = extract_json(f.read())
                state = PipelineState(**data)
            self.log_done(
                f"Simulation mode: Loaded market context for {len(state.market_context)} tickers."
            )
            return state
        else:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(self.collector._fetch_one, ticker): ticker
                    for ticker in watchlist
                }
                for future in as_completed(futures):
                    ticker = futures[future]
                    try:
                        snapshot = future.result()
                        if snapshot:
                            market_context[ticker] = snapshot
                    except Exception as e:
                        self.logger.warning(
                            f"[MarketData] {ticker}: snapshot failed — {e}"
                        )

            volume_spikes = self.collector.get_volume_spike_tickers(
                market_context, threshold=self.volume_spike
            )
            if volume_spikes:
                self.logger.info(
                    f"[MarketData] Volume spikes detected: {volume_spikes}"
                )

            self.log_done(
                f"Market data fetched for {len(market_context)}/{len(watchlist)} tickers. "
                f"{len(volume_spikes)} volume spike(s) detected."
            )
            state.market_context = market_context
        return state

    # ------------------------------------------------------------------
    # Helpers for downstream agents
    # ------------------------------------------------------------------

    @staticmethod
    def get_price_context_string(
        ticker: str,
        market_context: dict[str, MarketSnapshot],
    ) -> str:
        """
        Returns a human-readable price context string for injection into
        LLM summarization prompts.

        Example:
            "D05.SI: SGD 37.20 | 1D: +1.4% | 5D: -0.8% | Vol: 1.8x avg |
             Analyst: Buy | Target: SGD 42.00 | Next earnings: 2026-05-08"
        """
        snap = market_context.get(ticker)
        if not snap:
            return ""

        parts = [f"{ticker}:"]

        price = snap.get("last_price")
        if price is not None:
            currency = snap.get("currency", "SGD")
            parts.append(f"{currency} {price:.2f}")

        p1 = snap.get("price_change_1d")
        if p1 is not None:
            sign = "+" if p1 >= 0 else ""
            parts.append(f"1D: {sign}{p1:.1f}%")

        p5 = snap.get("price_change_5d")
        if p5 is not None:
            sign = "+" if p5 >= 0 else ""
            parts.append(f"5D: {sign}{p5:.1f}%")

        vr = snap.get("volume_ratio")
        if vr is not None:
            parts.append(f"Vol: {vr:.1f}x avg")

        rating = snap.get("analyst_rating")
        if rating:
            parts.append(f"Analyst: {rating}")

        target = snap.get("target_price")
        if target is not None:
            currency = snap.get("currency", "SGD")
            parts.append(f"Target: {currency} {target:.2f}")

        earnings = snap.get("earnings_date")
        if earnings:
            parts.append(f"Next earnings: {earnings}")

        return " | ".join(parts)

    @staticmethod
    def is_earnings_window(
        ticker: str,
        market_context: dict[str, MarketSnapshot],
        days_window: int = 7,
    ) -> bool:
        """
        Returns True if the ticker has earnings within ±days_window days.
        Used by ImportanceRankingAgent to boost pre/post-earnings news.
        """
        from datetime import datetime, timezone

        snap = market_context.get(ticker)
        if not snap or not snap.get("earnings_date"):
            return False

        try:
            earnings_dt = datetime.fromisoformat(snap["earnings_date"]).replace(
                tzinfo=timezone.utc
            )
            now = datetime.now(timezone.utc)
            delta = abs((earnings_dt - now).days)
            return delta <= days_window
        except Exception:
            return False
def market_data_agent(state: PipelineState) -> PipelineState:
    agent = MarketDataAgent({})
    return agent.run(state)