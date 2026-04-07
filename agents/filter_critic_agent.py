"""
agents/filter_critic_agent.py
------------------------------
Critic A — FilterCriticAgent

Evaluates Agent 3's (NoiseFilterAgent) output and decides:
  PASS  → proceed to Agent 4 (EventClusteringAgent)
  RETRY → send control back to Agent 3 with critique injected

Evaluation dimensions (weighted 0.0–1.0):
  signal_density   (35%) – fraction of articles scoring GPT-4o signal=3
  dedup_quality    (25%) – inverted residual-duplicate estimate
  recency_score    (15%) – fraction published in last 48 h
  source_diversity (15%) – unique sources / article count
  ticker_coverage  (10%) – watchlist tickers with ≥1 article

PASS threshold : score ≥ 0.55  OR  retry_count ≥ MAX_RETRIES
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

from core.base_agent import BaseAgent
from utils.llm import call_openai, extract_json
from core.state import PipelineState
from dotenv import load_dotenv
import os
load_dotenv()  # Load environment variables from .env file

MAX_RETRIES    = 2
PASS_THRESHOLD = 0.55

WEIGHTS = {
    "signal_density":   0.35,
    "dedup_quality":    0.25,
    "recency_score":    0.15,
    "source_diversity": 0.15,
    "ticker_coverage":  0.10,
}

CRITIC_PROMPT = """You are a quality-control critic for a financial news intelligence system.

{n} articles passed through a dedup/noise filter. Assess each article:

Signal scale:
  1 = Low  — generic, vague, no specific financial data
  2 = Med  — mentions company/ticker but no hard facts
  3 = High — contains specific financial data (numbers, events, decisions)

Also count residual duplicate PAIRS (articles clearly covering the same event).

Return ONLY JSON:
{{
  "article_scores":       [3, 1, 2, ...],
  "duplicate_pair_count": 2,
  "issues":      ["specific quality problems"],
  "suggestions": ["concrete changes Agent 3 should make on retry"]
}}

Articles:
{articles_text}"""


class FilterCriticAgent(BaseAgent):
    """
    Critic A: Evaluates NoiseFilterAgent output and issues PASS / RETRY verdict.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.openai_key  = os.getenv("OPENAI_API_KEY")
        self.pass_threshold = config.get("filter_pass_threshold", PASS_THRESHOLD)
        self.max_retries    = config.get("filter_critic_max_retries", MAX_RETRIES)

    # ── public entry point ────────────────────────────────────────────────────
    def run(self, state: PipelineState) -> PipelineState:
        retry_count = state.filter_retry_count
        articles    = state.cleaned_articles
        watchlist   = state.watchlist
        n           = len(articles)

        self.log_start(
            f"Evaluating {n} filtered articles "
            f"(attempt {retry_count + 1}/{self.max_retries + 1})"
        )
        state.current_step = 3
        state.step_logs.append(
            f"[Filter Critic] Evaluating filter quality — {n} articles "
            f"(attempt {retry_count + 1}/{self.max_retries + 1})..."
        )

        # ── edge case: no articles ────────────────────────────────────────────
        if n == 0:
            force = retry_count >= self.max_retries
            report = {
                "passed":      force,
                "score":       0.0,
                "verdict":     "PASS" if force else "RETRY",
                "issues":      ["No articles survived filtering — filter may be too aggressive"],
                "suggestions": ["Relax deduplication threshold", "Lower minimum snippet length"],
                "metrics":     {},
            }
            state.filter_critique = report
            state.step_logs.append(
                f"[Filter Critic] {'FORCE-PASS (max retries)' if force else 'RETRY — zero articles'}"
            )
            self.log_done("RETRY — zero articles" if not force else "FORCE-PASS")
            return state

        # ── heuristic metrics (no LLM) ────────────────────────────────────────
        heuristics = self._heuristic_metrics(articles, watchlist)

        # ── LLM signal + dedup evaluation ────────────────────────────────────
        signal_density = 0.60
        dedup_quality  = 0.70
        llm_issues: list[str]       = []
        llm_suggestions: list[str]  = []
        dup_pairs = 0

        try:
            sample = articles[:30]
            art_text = "\n".join(
                f"[{i}] [{a.get('ticker','')}] [{a.get('source','')}] "
                f"{a.get('headline','')} | {a.get('snippet','')[:120]}"
                for i, a in enumerate(sample)
            )
            resp   = call_openai(
                CRITIC_PROMPT.format(n=len(sample), articles_text=art_text),
                self.openai_key,
                temperature=0.1,
            )
            result = extract_json(resp)

            scores = result.get("article_scores", [])
            if scores:
                signal_density = round(sum(1 for s in scores if s == 3) / len(scores), 3)

            dup_pairs    = result.get("duplicate_pair_count", 0)
            dedup_quality = round(max(0.0, 1.0 - dup_pairs / max(len(sample) / 2, 1)), 3)
            llm_issues      = result.get("issues", [])
            llm_suggestions = result.get("suggestions", [])

        except Exception as e:
            self.logger.warning(f"LLM evaluation failed ({e}) — using heuristics only")

        # ── combine into overall score ────────────────────────────────────────
        metrics = {
            "signal_density":   signal_density,
            "dedup_quality":    dedup_quality,
            **heuristics,
            "article_count":    n,
            "retry_count":      retry_count,
        }
        score = round(sum(metrics.get(k, 0) * w for k, w in WEIGHTS.items()), 4)

        # ── synthesise issues & suggestions ───────────────────────────────────
        all_issues = list(llm_issues)
        all_sug    = list(llm_suggestions)

        if metrics.get("signal_density", 1) < 0.3:
            all_issues.append(
                f"Low signal density: only {signal_density:.0%} of articles are high-signal"
            )
            all_sug.append("Require specific numbers or named events for KEEP")
        if metrics.get("dedup_quality", 1) < 0.6:
            all_issues.append(f"Residual duplication: ~{dup_pairs} duplicate pairs detected")
            all_sug.append("Apply stricter near-duplicate matching across sources")
        if metrics.get("ticker_coverage", 1) < 0.5:
            all_issues.append(
                f"Poor ticker coverage: {metrics['ticker_coverage']:.0%} of watchlist covered"
            )
            all_sug.append("Ensure at least one article per watchlist ticker is retained")

        force_pass = retry_count >= self.max_retries
        passed     = force_pass or (score >= self.pass_threshold)
        verdict    = "PASS" if passed else "RETRY"

        report = {
            "passed":      passed,
            "score":       score,
            "verdict":     verdict,
            "issues":      all_issues,
            "suggestions": all_sug,
            "metrics":     metrics,
        }
        state.filter_critique = report

        verdict_msg = (
            f"FORCE-PASS after {retry_count} retries" if force_pass
            else f"PASS (score {score:.3f} ≥ {self.pass_threshold})" if passed
            else f"RETRY (score {score:.3f} < {self.pass_threshold}) — {len(all_issues)} issue(s)"
        )
        state.step_logs.append(f"[Filter Critic] {verdict_msg}")
        if all_issues and not passed:
            for issue in all_issues[:3]:
                state.step_logs.append(f"[Filter Critic]   ✗ {issue}")

        self.log_done(verdict_msg)
        return state

    # ── helpers ───────────────────────────────────────────────────────────────
    @staticmethod
    def _heuristic_metrics(articles: list[dict], watchlist: list[str]) -> dict:
        n = len(articles)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=48)

        recent = 0
        for a in articles:
            try:
                dt = datetime.fromisoformat(a.get("published_at","").replace("Z","+00:00"))
                if dt >= cutoff:
                    recent += 1
            except Exception:
                pass

        unique_sources = len({a.get("source","") for a in articles})
        covered        = {a.get("ticker","") for a in articles}

        return {
            "recency_score":    round(recent / n, 3),
            "source_diversity": round(min(unique_sources / n, 1.0), 3),
            "ticker_coverage":  round(len(covered & set(watchlist)) / max(len(watchlist), 1), 3),
        }


# ── LangGraph node wrapper + router ──────────────────────────────────────────
def filter_critic_agent(state: PipelineState) -> PipelineState:
    agent = FilterCriticAgent({
        "openai_key":    os.getenv("OPENAI_API_KEY"),
        "pass_threshold": PASS_THRESHOLD,
        "max_retries":    MAX_RETRIES,
    })
    return agent.run(state)


def route_after_filter_critic(state: PipelineState) -> str:
    if state.errors:
        return "abort"
    critique = state.filter_critique
    return "retry_filter" if not critique.get("passed", True) else "continue"