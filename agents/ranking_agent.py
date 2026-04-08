"""
agents/ranking_agent.py
-----------------------
Agent 6 — ImportanceRankingAgent

Scores every event card 0.0–1.0 and assigns High / Medium / Low label.
On RETRY: reads ranking_critique.suggestions and recalibrates thresholds.

Formula (spec):
  score = event_type_weight × 0.40
        + corroboration     × 0.25
        + novelty           × 0.20
        + credibility       × 0.15
        + confidence_adj + volume_bonus + earnings_proximity_bonus
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from utils.llm import call_openai, extract_json
from core.base_agent import BaseAgent
from core.state import PipelineState


EVENT_TYPE_WEIGHTS: dict[str, float] = {
    "earnings_release": 0.95, 
    "dividend": 0.75, 
    "guidance_update": 0.85,
    "ma_announcement":  0.90, 
    "regulatory_action": 0.80, 
    "capital_action": 0.75,
    "leadership_change": 0.70, 
    "litigation": 0.70, 
    "product_launch": 0.60,
    "analyst_rating":   0.60, 
    "general_news": 0.35,
    # legacy aliases
    "earnings": 0.95, "guidance": 0.85, "M&A": 0.90,
    "regulation": 0.80, "macro": 0.50, "market_trend": 0.40, "other": 0.35,
}

SOURCE_CREDIBILITY: dict[str, float] = {
    "sgx": 1.00, 
    "mas": 1.00,
    "business times": 0.85, 
    "straits times": 0.85, 
    "reuters": 0.85, 
    "bloomberg": 0.85,
    "cna": 0.70, 
    "nikkei": 0.70, 
    "cnbc": 0.70, 
    "seeking alpha": 0.70,
    "yahoo": 0.55, 
    "finviz": 0.55,
}
DEFAULT_CRED = 0.55

# Default thresholds
HIGH_T_DEFAULT = 0.70
MED_T_DEFAULT  = 0.45


class ImportanceRankingAgent(BaseAgent):
    """
    Agent 6: Multi-signal importance scorer with critique-driven recalibration.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.high_t = config.get("high_threshold", HIGH_T_DEFAULT)
        self.med_t  = config.get("med_threshold",  MED_T_DEFAULT)
        self.simulation_mode = config.get("simulation_mode", True)

    def run(self, state: PipelineState) -> PipelineState:
        try:
            retry_count    = state.ranking_retry_count
            critique       = state.ranking_critique
            market_context = state.market_context
            cards          = state.event_cards

            self.log_start(
                f"{len(cards)} event cards"
                + (f" [retry #{retry_count}]" if retry_count else "")
            )
            state.current_step = 6

            if self.simulation_mode:
                with open("ranking_test_output.json", "r",  encoding='utf-8') as f:
                    data = extract_json(f.read())
                    state = PipelineState(**data)
                    cards = state.event_cards
                    msg = f"[Agent 6] ✓ Ranked {len(cards)} events (simulated)"
                    state.step_logs.append(msg)
                    self.log_done(msg)
                    return state

            if retry_count == 0:
                state.step_logs.append("[Agent 6] Scoring and ranking events...")
            else:
                issues = "; ".join((critique or {}).get("issues", [])[:2])
                state.step_logs.append(
                    f"[Agent 6] RETRY #{retry_count} — Critic B said: {issues or 'ranking quality too low'}"
                )

            # Score all cards
            for card in cards:
                score, signals = self._score_card(card, market_context)
                card["importance_score"] = score
                card["scoring_signals"]  = signals

            cards.sort(key=lambda c: c["importance_score"], reverse=True)

            # Calibrate thresholds (may adjust on retry)
            high_t, med_t = self._calibrated_thresholds(critique, cards)
            if retry_count > 0:
                state.step_logs.append(
                    f"[Agent 6] Recalibrated thresholds: High≥{high_t}, Medium≥{med_t}"
                )

            # Assign labels and ranks
            for i, card in enumerate(cards):
                card["importance"]   = self._label(card["importance_score"], high_t, med_t)
                card["rank_overall"] = i + 1

            ticker_ctr: dict[str, int] = {}
            for card in cards:
                t = card.get("ticker", "")
                ticker_ctr[t] = ticker_ctr.get(t, 0) + 1
                card["rank_per_ticker"] = ticker_ctr[t]

            state.ranking_retry_count = retry_count + 1
            state.ranked_digest       = cards

            high   = sum(1 for c in cards if c["importance"] == "High")
            medium = sum(1 for c in cards if c["importance"] == "Medium")
            low    = sum(1 for c in cards if c["importance"] == "Low")
            msg = (
                f"[Agent 6] ✓ Ranked {len(cards)} events — "
                f"{high} High / {medium} Medium / {low} Low "
                f"(thresholds: High≥{high_t}, Med≥{med_t})"
            )
            state.step_logs.append(msg)
            self.log_done(msg)
        except Exception as e:
            self.logger.error(f"Failed: {e}")
            state.errors.append(f"[Agent 6] failed: {e}")
        return state

    # ── scoring ───────────────────────────────────────────────────────────────
    def _score_card(self, card: dict, mctx: dict) -> tuple[float, dict]:
        ticker = card.get("ticker", "")
        et_w   = EVENT_TYPE_WEIGHTS.get(card.get("event_type","general_news"), 0.35)
        srcs   = card.get("supporting_sources", [])
        corr   = min(len(set(srcs)) / 5, 1.0)
        nov    = min(card.get("article_count", 1) / 8, 1.0)
        cred   = sum(self._src_cred(s) for s in srcs) / max(len(srcs), 1) if srcs else DEFAULT_CRED
        conf_adj = {"high": 0.05, "medium": 0.0, "low": -0.05}.get(card.get("confidence","medium"), 0.0)
        vol_b  = 0.05 if (mctx.get(ticker, {}).get("volume_ratio") or 0) > 2.0 else 0.0
        earn_b = self._earnings_bonus(ticker, mctx)

        raw = round(min(max(
            et_w * 0.40 + corr * 0.25 + nov * 0.20 + cred * 0.15
            + conf_adj + vol_b + earn_b
        , 0.0), 1.0), 4)

        return raw, {
            "event_type_weight":        et_w,
            "corroboration_count":      len(set(srcs)),
            "corroboration_score":      round(corr, 3),
            "novelty_score":            round(nov, 3),
            "credibility_score":        round(cred, 3),
            "confidence_adj":           conf_adj,
            "volume_bonus":             vol_b,
            "earnings_proximity_bonus": earn_b,
        }

    @staticmethod
    def _src_cred(source: str) -> float:
        sl = source.lower()
        return next((v for k, v in SOURCE_CREDIBILITY.items() if k in sl), DEFAULT_CRED)

    @staticmethod
    def _earnings_bonus(ticker: str, mctx: dict) -> float:
        ed = mctx.get(ticker, {}).get("earnings_date")
        if not ed:
            return 0.0
        try:
            dt = datetime.fromisoformat(ed)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return 0.05 if abs((dt - datetime.now(timezone.utc)).days) <= 7 else 0.0
        except ValueError:
            return 0.0

    @staticmethod
    def _label(score: float, high_t: float, med_t: float) -> str:
        return "High" if score >= high_t else "Medium" if score >= med_t else "Low"

    @staticmethod
    def _calibrated_thresholds(critique: dict | None, events: list[dict]) -> tuple[float, float]:
        high_t, med_t = HIGH_T_DEFAULT, MED_T_DEFAULT
        if not critique or not critique.get("suggestions"):
            return high_t, med_t
        text = " ".join(critique.get("suggestions", [])).lower()
        if "too many high" in text or "all high" in text:
            high_t = min(high_t + 0.08, 0.85); med_t = min(med_t + 0.05, 0.65)
        elif "too few high" in text or "all low" in text:
            high_t = max(high_t - 0.08, 0.50); med_t = max(med_t - 0.05, 0.30)
        if ("differentiation" in text or "compressed" in text) and len(events) >= 3:
            n = len(events)
            scores = sorted([e.get("importance_score", 0) for e in events], reverse=True)
            high_t = scores[max(0, n // 4)]
            med_t  = scores[max(0, n // 2)]
        return round(high_t, 3), round(med_t, 3)


# ── LangGraph node wrapper ─────────────────────────────────────────────────────
def ranking_agent(state: PipelineState) -> PipelineState:
    agent = ImportanceRankingAgent({})
    return agent.run(state)