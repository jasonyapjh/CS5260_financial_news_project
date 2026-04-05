"""
Agent 6: ImportanceRankingAgent
Scores every event card 0-1 and assigns High / Medium / Low label.

Scoring formula (from spec):
  score = event_type_weight  × 0.40
        + corroboration_score × 0.25
        + novelty_score       × 0.20
        + credibility_score   × 0.15
        + confidence_adj

Signals:
  event_type_weight (40%) – fixed weights per event_type
  corroboration     (25%) – unique source count / 5, capped at 1.0
  novelty           (20%) – article_count / 8, capped at 1.0
  credibility       (15%) – avg credibility tier of supporting sources
  confidence_adj          – +0.05 high / 0 medium / -0.05 low
  volume_ratio bonus      – +0.05 if volume_ratio > 2.0 (from market_context)
  earnings_proximity bonus– +0.05 if within ±7 days of earnings_date

Thresholds:
  ≥ 0.70 → High
  ≥ 0.45 → Medium
  <  0.45 → Low

Adds to each event card:
  importance, importance_score (0-1), rank_overall, rank_per_ticker,
  scoring_signals { event_type_weight, corroboration_count, corroboration_score,
                    novelty_score, credibility_score, confidence_adj }
"""

from datetime import datetime, timezone, timedelta
from utils.state import PipelineState


# ── Event type weights (spec Table) ──────────────────────────────────────────
EVENT_TYPE_WEIGHTS: dict[str, float] = {
    "earnings_release":  0.95,
    "dividend":          0.75,
    "guidance_update":   0.85,
    "ma_announcement":   0.90,
    "regulatory_action": 0.80,
    "capital_action":    0.75,
    "leadership_change": 0.70,
    "litigation":        0.70,
    "product_launch":    0.60,
    "analyst_rating":    0.60,
    "general_news":      0.35,
    # Legacy / fallback keys
    "earnings":          0.95,
    "guidance":          0.85,
    "M&A":               0.90,
    "regulation":        0.80,
    "macro":             0.50,
    "market_trend":      0.40,
    "other":             0.35,
}

# Source credibility lookup (must match retrieval_agent)
SOURCE_CREDIBILITY: dict[str, float] = {
    "sgx":           1.00, "mas":           1.00,
    "business times":0.85, "straits times": 0.85,
    "reuters":       0.85, "bloomberg":     0.85,
    "cna":           0.70, "nikkei":        0.70, "cnbc": 0.70,
    "yahoo":         0.55, "singapore business review": 0.55,
}
DEFAULT_CRED = 0.55


def _source_credibility(source_name: str) -> float:
    sl = source_name.lower()
    for key, score in SOURCE_CREDIBILITY.items():
        if key in sl:
            return score
    return DEFAULT_CRED


def _confidence_adj(confidence: str) -> float:
    return {"high": 0.05, "medium": 0.0, "low": -0.05}.get(confidence, 0.0)


def _volume_bonus(ticker: str, market_context: dict) -> float:
    ctx = market_context.get(ticker, {})
    return 0.05 if (ctx.get("volume_ratio") or 0) > 2.0 else 0.0


def _earnings_proximity_bonus(ticker: str, market_context: dict) -> float:
    ctx = market_context.get(ticker, {})
    ed  = ctx.get("earnings_date")
    if not ed:
        return 0.0
    try:
        earnings_dt = datetime.fromisoformat(ed)
        if earnings_dt.tzinfo is None:
            earnings_dt = earnings_dt.replace(tzinfo=timezone.utc)
        delta = abs((earnings_dt - datetime.now(timezone.utc)).days)
        return 0.05 if delta <= 7 else 0.0
    except ValueError:
        return 0.0


def _score_card(card: dict, market_context: dict) -> tuple[float, dict]:
    """Return (raw_score, scoring_signals_dict)."""
    ticker = card.get("ticker", "")

    # Event type weight
    et     = card.get("event_type", "general_news")
    et_w   = EVENT_TYPE_WEIGHTS.get(et, 0.35)

    # Corroboration: unique source count / 5
    sources       = card.get("supporting_sources", [])
    corr_count    = len(set(sources))
    corr_score    = min(corr_count / 5, 1.0)

    # Novelty: article_count / 8
    novelty_score = min(card.get("article_count", 1) / 8, 1.0)

    # Credibility: average tier score across supporting sources
    cred_scores   = [_source_credibility(s) for s in sources] if sources else [DEFAULT_CRED]
    cred_score    = sum(cred_scores) / len(cred_scores)

    # Confidence adjustment
    conf_adj      = _confidence_adj(card.get("confidence", "medium"))

    # Bonuses from market context
    vol_bonus     = _volume_bonus(ticker, market_context)
    earn_bonus    = _earnings_proximity_bonus(ticker, market_context)

    raw_score = (
        et_w        * 0.40 +
        corr_score  * 0.25 +
        novelty_score * 0.20 +
        cred_score  * 0.15 +
        conf_adj    +
        vol_bonus   +
        earn_bonus
    )
    raw_score = min(max(raw_score, 0.0), 1.0)

    signals = {
        "event_type_weight":   et_w,
        "corroboration_count": corr_count,
        "corroboration_score": round(corr_score, 3),
        "novelty_score":       round(novelty_score, 3),
        "credibility_score":   round(cred_score, 3),
        "confidence_adj":      conf_adj,
        "volume_bonus":        vol_bonus,
        "earnings_proximity_bonus": earn_bonus,
    }
    return round(raw_score, 4), signals


def _label(score: float) -> str:
    if score >= 0.70:
        return "High"
    if score >= 0.45:
        return "Medium"
    return "Low"


def ranking_agent(state: PipelineState) -> PipelineState:
    state["current_step"] = 6
    state["step_logs"].append("[Agent 6] Scoring and ranking events...")

    cards          = state.get("event_cards", [])
    market_context = state.get("market_context", {})

    # Score every card
    for card in cards:
        score, signals = _score_card(card, market_context)
        card["importance_score"]   = score
        card["importance"]         = _label(score)
        card["scoring_signals"]    = signals

    # Overall rank (descending score)
    cards.sort(key=lambda c: c["importance_score"], reverse=True)
    for i, card in enumerate(cards):
        card["rank_overall"] = i + 1

    # Per-ticker rank
    ticker_counters: dict[str, int] = {}
    for card in cards:
        t = card.get("ticker", "")
        ticker_counters[t] = ticker_counters.get(t, 0) + 1
        card["rank_per_ticker"] = ticker_counters[t]

    state["ranked_events"] = cards
    high   = sum(1 for c in cards if c["importance"] == "High")
    medium = sum(1 for c in cards if c["importance"] == "Medium")
    low    = sum(1 for c in cards if c["importance"] == "Low")
    state["step_logs"].append(
        f"[Agent 6] ✓ Ranked {len(cards)} events — "
        f"{high} High / {medium} Medium / {low} Low"
    )
    return state
