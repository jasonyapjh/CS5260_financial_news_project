"""
agents/filter_agent.py
----------------------
Agent 3 — NoiseFilterAgent

Matches the uploaded class structure exactly. Three passes:
  Pass 1 — Hard filters  (URL dedup, snippet length, recency, headline hash)
  Pass 2 — Semantic dedup (sentence-transformers embeddings, lazy-loaded)
  Pass 3 — LLM quality filter (GPT-4o, optional, enabled by config)

On RETRY (filter_retry_count > 0): critic feedback injected into Pass 3 prompt.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta, timezone

import numpy as np

from core.base_agent import BaseAgent
from utils.llm import call_openai, extract_json
from core.state import PipelineState
from dotenv import load_dotenv
load_dotenv()

class NoiseFilterAgent(BaseAgent):
    """
    Agent 3: Three-pass noise filter and deduplicator.
    Inherits BaseAgent; sentence-transformers loaded lazily.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        filt = config.get("filtering", {})
        retr = config.get("retrieval", {})
        clus = config.get("clustering", {})

        self.min_snippet_len = filt.get("min_snippet_length", 50)
        self.sim_threshold   = filt.get("similarity_threshold", 0.85)
        self.lookback_hours  = retr.get("lookback_hours", 24 * 7)
        self.embedding_model = clus.get(
            "embedding_model", "sentence-transformers/all-MiniLM-L6-v2"
        )
        self.llm_enabled = filt.get("llm_enabled", True)
        self.openai_key  = os.getenv("OPENAI_API_KEY")

        self._model        = None   # lazy-loaded SentenceTransformer
        self._embeddings_ok = None  # None = not yet tested

    # ── public entry point ────────────────────────────────────────────────────
    def run(self, state: PipelineState) -> PipelineState:
        retry_count = state.filter_retry_count
        critique    = state.filter_critique

        self.log_start(
            f"{state.raw_article_count} raw articles"
            + (f" [retry #{retry_count}]" if retry_count else "")
        )
        state.current_step = 3

        if retry_count == 0:
            state.step_logs.append("[Agent 3] Running Pass 1 (hard filters)...")
        else:
            issues = "; ".join((critique or {}).get("issues", [])[:2])
            state.step_logs.append(
                f"[Agent 3] RETRY #{retry_count} — Critic A said: {issues or 'quality too low'}"
            )

        # Always restart from raw_articles so each retry is a clean attempt
        raw = state.raw_articles

        articles = self._hard_filter(raw)
        self.logger.info(f"After hard filters: {len(articles)} articles")
        state.step_logs.append(
            f"[Agent 3] Pass 1: {len(raw)} → {len(articles)} articles"
        )

        articles = self._semantic_deduplicate(articles)
        self.logger.info(f"After semantic dedup: {len(articles)} articles")

        if self.llm_enabled and self.openai_key and articles:
            state.step_logs.append(
                "[Agent 3] Pass 3 (LLM quality filter"
                + (", with critic feedback" if retry_count > 0 and critique else "")
                + ")..."
            )
            articles = self._llm_quality_filter(articles, critique)
            self.logger.info(f"After LLM filtering: {len(articles)} articles")

        state.filter_retry_count = retry_count + 1
        state.cleaned_articles = articles
        state.clean_article_count = len(articles)

        msg = f"[Agent 3] ✓ {len(articles)} articles retained after all passes"
        state.step_logs.append(msg)
        self.log_done(msg)
        return state

    # ── Pass 1: Hard filters ──────────────────────────────────────────────────
    def _hard_filter(self, articles: list[dict]) -> list[dict]:
        cutoff      = datetime.now(timezone.utc) - timedelta(hours=self.lookback_hours)
        seen_urls   : set[str] = set()
        seen_hashes : set[str] = set()
        kept = []

        for a in articles:
            url      = (a.get("url") or "").strip()
            headline = (a.get("headline") or "").strip()

            h_key = hashlib.md5(headline.lower().encode()).hexdigest()
            if not url or url in seen_urls or h_key in seen_hashes:
                continue

            # Accept if full_text or snippet meets minimum length
            has_content = (
                len((a.get("full_text") or "").strip()) >= self.min_snippet_len
                or len((a.get("snippet") or "").strip()) >= self.min_snippet_len
            )
            if not has_content:
                continue

            pub = a.get("published_at", "")
            if pub:
                try:
                    dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                    if dt < cutoff:
                        continue
                except Exception:
                    pass

            seen_urls.add(url)
            seen_hashes.add(h_key)
            kept.append(a)

        return kept

    # ── Pass 2: Semantic deduplication ───────────────────────────────────────
    def _semantic_deduplicate(self, articles: list[dict]) -> list[dict]:
        if not self._check_embeddings_available() or not articles:
            return articles

        by_ticker: dict[str, list[dict]] = {}
        for a in articles:
            by_ticker.setdefault(a.get("ticker") or "GENERAL", []).append(a)

        result = []
        for group in by_ticker.values():
            result.extend(self._dedup_group(group))
        return result

    def _dedup_group(self, articles: list[dict]) -> list[dict]:
        if len(articles) <= 1:
            return articles
        try:
            model    = self._get_model()
            articles = sorted(articles, key=self._source_tier, reverse=True)
            texts    = [
                f"{a.get('headline','')} "
                f"{(a.get('full_text') or a.get('snippet') or '')[:200]}"
                for a in articles
            ]
            embeddings = model.encode(texts, normalize_embeddings=True)

            kept = []
            dropped: set[int] = set()
            for i in range(len(articles)):
                if i in dropped:
                    continue
                kept.append(articles[i])
                for j in range(i + 1, len(articles)):
                    if j in dropped:
                        continue
                    if float(np.dot(embeddings[i], embeddings[j])) >= self.sim_threshold:
                        dropped.add(j)
            return kept
        except Exception as e:
            self.logger.warning(f"Semantic dedup failed: {e}")
            return articles

    # ── Pass 3: LLM quality filter ────────────────────────────────────────────
    _BASE_PROMPT = """Return a JSON array of indices to KEEP.
DROP articles that are: Clickbait, generic market roundups, or low-signal fluff.
KEEP articles with: Specific financial data, M&A news, or regulatory updates.
{critique_section}
Articles:
{text}"""

    def _llm_quality_filter(
        self,
        articles: list[dict],
        critique: dict | None = None,
    ) -> list[dict]:
        critique_section = self._build_critique_section(critique)
        batch_size = 20
        final_kept: list[dict] = []

        for i in range(0, len(articles), batch_size):
            batch = articles[i : i + batch_size]
            batch_text = "\n".join(
                f"[{idx}] {a.get('headline','')} | "
                f"{(a.get('full_text') or a.get('snippet') or '')[:150]}"
                for idx, a in enumerate(batch)
            )
            try:
                resp   = call_openai(
                    self._BASE_PROMPT.format(
                        critique_section=critique_section,
                        text=batch_text,
                    ),
                    self.openai_key,
                )
                valid  = extract_json(resp)
                final_kept.extend(batch[idx] for idx in valid if idx < len(batch))
            except Exception as e:
                self.logger.error(f"LLM batch failed: {e} — keeping batch")
                final_kept.extend(batch)

        return final_kept

    @staticmethod
    def _build_critique_section(critique: dict | None) -> str:
        if not critique or not critique.get("suggestions"):
            return ""
        lines = [
            "IMPORTANT — Previous attempt was rated too low. Apply these corrections:"
        ]
        for issue in (critique.get("issues") or [])[:3]:
            lines.append(f"  ✗ {issue}")
        for sug in (critique.get("suggestions") or [])[:4]:
            lines.append(f"  → Fix: {sug}")
        return "\n".join(lines)

    # ── Embedding helpers ─────────────────────────────────────────────────────
    def _check_embeddings_available(self) -> bool:
        if self._embeddings_ok is not None:
            return self._embeddings_ok
        try:
            import sentence_transformers  # noqa: F401
            import numpy                  # noqa: F401
            self._embeddings_ok = True
        except Exception as e:
            self.logger.warning(
                f"sentence-transformers unavailable — skipping semantic dedup: {e}\n"
                "To enable: pip install 'numpy<2' && pip install sentence-transformers"
            )
            self._embeddings_ok = False
        return self._embeddings_ok

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self.logger.info(f"Loading embedding model: {self.embedding_model}")
            self._model = SentenceTransformer(self.embedding_model)
        return self._model

    @staticmethod
    def _source_tier(article: dict) -> int:
        tiers = {
            "SGX Announcements": 4, "MAS": 4,
            "Business Times": 3, "Straits Times": 3, "Reuters": 3,
            "Bloomberg": 3, "Financial Times": 3,
            "CNA": 2, "Nikkei Asia": 2, "CNBC": 2,
            "Seeking Alpha": 2, "Yahoo Finance": 1, "Finviz": 1,
        }
        return tiers.get(article.get("source", ""), 1)


# ── LangGraph node wrapper ─────────────────────────────────────────────────────
def filter_agent(state: PipelineState) -> PipelineState:
    config = {
        "openai_key": os.getenv("OPENAI_API_KEY"),
        "filtering": {"llm_enabled": True, "min_snippet_length": 20},
        "retrieval": {"lookback_hours": 24 * 7},
        "clustering": {"embedding_model": "sentence-transformers/all-MiniLM-L6-v2"},
    }
    agent = NoiseFilterAgent(config)
    return agent.run(state)