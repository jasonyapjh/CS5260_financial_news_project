"""
agents/ranking_critic_agent.py
-------------------------------
RankingCriticAgent

Evaluates Agent 6's (ImportanceRankingAgent) output and decides:
  PASS  → proceed to Agent 7 (NotificationAgent)
  RETRY → send control back to Agent 6 with recalibration hints

Evaluation dimensions (weighted 0.0–1.0):
  top_coherence    (30%) – LLM: do top-3 events deserve to be highest-ranked?
  score_spread     (25%) – std dev of importance_scores (low = poor differentiation)
  label_balance    (20%) – Shannon entropy of High/Medium/Low distribution
  bottom_coherence (15%) – LLM: are bottom events genuinely low-importance?
  confidence_align (10%) – high-confidence cards should rank higher on average

PASS threshold : score ≥ 0.55  OR  retry_count ≥ MAX_RETRIES
"""

from __future__ import annotations

import math

from core.base_agent import BaseAgent
from utils.llm import call_openai, extract_json
from core.state import PipelineState
import os
from dotenv import load_dotenv
load_dotenv()

MAX_RETRIES    = 2
PASS_THRESHOLD = 0.55

WEIGHTS = {
    "top_coherence":     0.30,
    "score_spread":      0.25,
    "label_balance":     0.20,
    "bottom_coherence":  0.15,
    "confidence_align":  0.10,
}

COHERENCE_PROMPT = """You are a senior portfolio manager reviewing an AI-generated ranking of financial news events.

Assess whether the ranking is coherent for an equity investor.

Top-ranked events (should be most material):
{top_events}

Bottom-ranked events (should be least material):
{bottom_events}

Rate each group and flag misplacements.

Return ONLY JSON:
{{
  "top_coherence_score":    0.8,
  "bottom_coherence_score": 0.7,
  "misplacements": [
    {{"event": "brief description", "current_rank": 1, "should_be": "Low", "reason": "..."}}
  ],
  "issues":      ["ranking quality problems"],
  "suggestions": ["concrete recalibration hints for retry"]
}}"""


class RankingCriticAgent(BaseAgent):
    """
    Critic B: Evaluates ImportanceRankingAgent output and issues PASS / RETRY.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.openai_key    = os.getenv("OPENAI_API_KEY", "")
        self.pass_threshold = config.get("pass_threshold", PASS_THRESHOLD)
        self.max_retries    = config.get("max_retries", MAX_RETRIES)

    # ── public entry point ────────────────────────────────────────────────────
    def run(self, state: PipelineState) -> PipelineState:
        retry_count = state.ranking_retry_count
        events      = state.ranked_digest
        n           = len(events)

        self.log_start(
            f"Evaluating {n} ranked events "
            f"(attempt {retry_count + 1}/{self.max_retries + 1})"
        )
        state.current_step = 10
        state.step_logs.append(
            f"[Ranking Critic] Evaluating ranking quality — {n} events "
            f"(attempt {retry_count + 1}/{self.max_retries + 1})..."
        )

        if n == 0:
            state.ranking_critique = {
                "passed": True, "score": 1.0, "verdict": "PASS",
                "issues": [], "suggestions": [], "metrics": {},
            }
            state.step_logs.append("[Ranking Critic] PASS — no events to rank")
            self.log_done("PASS — no events")
            return state

        # Heuristic metrics
        spread   = self._score_spread(events)
        balance  = self._label_balance(events)
        conf_aln = self._confidence_alignment(events)

        # LLM coherence
        top_coh = bot_coh = 0.70
        llm_issues: list[str]      = []
        llm_sug: list[str]         = []
        misplacements: list[dict]  = []

        try:
            top_n = min(3, n); bot_n = min(3, n)

            def fmt(e):
                return (
                    f"  Rank {e.get('rank_overall','?')} [{e.get('importance','?')}] "
                    f"score={e.get('importance_score',0):.3f} | "
                    f"{e.get('ticker','')} | {e.get('event_type','')} | "
                    f"{e.get('representative_headline','') or e.get('tldr','')[:80]}"
                )

            resp   = call_openai(
                COHERENCE_PROMPT.format(
                    top_events="\n".join(fmt(e) for e in events[:top_n]),
                    bottom_events="\n".join(fmt(e) for e in events[-bot_n:]),
                ),
                self.openai_key,
                temperature=0.1,
            )
            result       = extract_json(resp)
            top_coh      = float(result.get("top_coherence_score", 0.70))
            bot_coh      = float(result.get("bottom_coherence_score", 0.70))
            llm_issues   = result.get("issues", [])
            llm_sug      = result.get("suggestions", [])
            misplacements= result.get("misplacements", [])
        except Exception as e:
            self.logger.warning(f"LLM coherence check failed ({e}) — using heuristics only")

        metrics = {
            "score_spread":      spread,
            "label_balance":     balance,
            "top_coherence":     round(top_coh, 3),
            "bottom_coherence":  round(bot_coh, 3),
            "confidence_align":  conf_aln,
            "event_count":       n,
            "retry_count":       retry_count,
            "label_distribution": {
                lbl: sum(1 for e in events if e.get("importance") == lbl)
                for lbl in ("High","Medium","Low")
            },
        }
        score = round(sum(metrics.get(k, 0) * w for k, w in WEIGHTS.items()), 4)

        all_issues = list(llm_issues)
        all_sug    = list(llm_sug)

        if spread < 0.3:
            all_issues.append(f"Poor score differentiation: stdev={spread:.3f}")
            all_sug.append("Widen scoring differentiation — currently too compressed")
        if balance < 0.4:
            dist = metrics["label_distribution"]
            all_issues.append(f"Skewed label distribution: {dist}")
            all_sug.append("Recalibrate High/Medium/Low thresholds for better balance")
        if conf_aln < 0.5:
            all_issues.append("High-confidence events ranking below low-confidence ones")
        for m in misplacements[:2]:
            all_issues.append(
                f"Misplaced: '{m.get('event','')}' at rank {m.get('current_rank','?')} "
                f"— should be {m.get('should_be','?')}"
            )

        force_pass = retry_count >= self.max_retries
        passed     = force_pass or (score >= self.pass_threshold)
        verdict    = "PASS" if passed else "RETRY"

        state.ranking_critique = {
            "passed":      passed,
            "score":       score,
            "verdict":     verdict,
            "issues":      all_issues,
            "suggestions": all_sug,
            "metrics":     metrics,
        }

        verdict_msg = (
            f"FORCE-PASS after {retry_count} retries" if force_pass
            else f"PASS (score {score:.3f} ≥ {self.pass_threshold})" if passed
            else f"RETRY (score {score:.3f} < {self.pass_threshold}) — {len(all_issues)} issue(s)"
        )
        state.step_logs.append(f"[Ranking Critic] {verdict_msg}")
        if all_issues and not passed:
            for issue in all_issues[:3]:
                state.step_logs.append(f"[Ranking Critic]   ✗ {issue}")

        self.log_done(verdict_msg)
        return state

    # ── heuristic metrics ─────────────────────────────────────────────────────
    @staticmethod
    def _score_spread(events: list[dict]) -> float:
        scores = [e.get("importance_score", 0.0) for e in events]
        if len(scores) < 2:
            return 1.0
        mean  = sum(scores) / len(scores)
        stdev = math.sqrt(sum((s - mean) ** 2 for s in scores) / len(scores))
        return round(min(stdev / 0.20, 1.0), 3)

    @staticmethod
    def _label_balance(events: list[dict]) -> float:
        n = len(events)
        if n == 0:
            return 0.0
        counts = {lbl: sum(1 for e in events if e.get("importance") == lbl)
                  for lbl in ("High","Medium","Low")}
        fracs  = [c / n for c in counts.values()]
        entropy = -sum(f * math.log(f + 1e-9) for f in fracs)
        return round(entropy / math.log(3), 3)

    @staticmethod
    def _confidence_alignment(events: list[dict]) -> float:
        if not events:
            return 1.0
        n = len(events)
        conf_val = {"high": 2, "medium": 1, "low": 0}
        high_ranks = [e.get("rank_overall", n) for e in events if conf_val.get(e.get("confidence","low"),0) == 2]
        low_ranks  = [e.get("rank_overall", n) for e in events if conf_val.get(e.get("confidence","low"),0) == 0]
        if not high_ranks or not low_ranks:
            return 0.8
        avg_high = sum(high_ranks) / len(high_ranks)
        avg_low  = sum(low_ranks)  / len(low_ranks)
        if avg_high < avg_low:
            return 1.0
        return round(max(0.0, 1.0 - (avg_high / max(avg_low, 1) - 1.0)), 3)


# ── LangGraph node wrapper + router ──────────────────────────────────────────
def ranking_critic_agent(state: PipelineState) -> PipelineState:
    agent = RankingCriticAgent({
        "openai_key":    state["openai_key"],
        "pass_threshold": PASS_THRESHOLD,
        "max_retries":    MAX_RETRIES,
    })
    return agent.run(state)


def route_after_ranking_critic(state: PipelineState) -> str:
    if state.errors:
        return "abort"
    critique = state.ranking_critique
    return "retry_ranking" if not critique.get("passed", True) else "continue"