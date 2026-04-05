"""
Agent 3: NoiseFilterAgent
Two-pass deduplication and quality filtering as per the data flow spec.

Pass 1 — Hard filters (heuristic, no LLM):
  - Exact URL dedup
  - Snippet length < 20 chars → drop
  - Age > lookback_hours → drop
  - Exact headline hash dedup

Pass 2 — Semantic deduplication (GPT-4o):
  - Near-duplicate headlines (same event, different phrasing) → keep highest-tier source
  - Low-signal content (roundups, clickbait, irrelevant) → drop

Output: same canonical article schema, fewer articles.
"""

import hashlib
from datetime import datetime, timedelta, timezone

from utils.llm import call_openai, extract_json
from utils.state import PipelineState


LOOKBACK_HOURS = 7 * 24   # 7 days default

DEDUP_PROMPT = """You are a financial news editor reviewing articles for a Singapore investor intelligence system.

Return the indices (0-based) of articles to KEEP.

DROP if:
- Near-duplicate of another article (same event reported by multiple sources — keep the one with the most informative snippet, or the highest-credibility source)
- Generic market roundup with no company-specific signal
- Clickbait or irrelevant to financial investing
- Snippet is vague with no factual content

KEEP if:
- Contains specific financial data (earnings, guidance, M&A, regulatory action, analyst rating, leadership change, product launch)
- Source is authoritative (SGX announcements, major business press)
- Unique angle not covered by other articles in the list

Return ONLY a JSON array of integer indices. Example: [0, 2, 5, 8]

Articles:
{articles_text}"""


def _pass1_hard_filter(articles: list[dict], lookback_hours: int = LOOKBACK_HOURS) -> list[dict]:
    """Hard filters: URL dedup, snippet length, recency, headline hash."""
    seen_urls:      set[str] = set()
    seen_headlines: set[str] = set()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    out: list[dict] = []

    for art in articles:
        url      = (art.get("url") or "").strip()
        headline = (art.get("headline") or "").strip()
        snippet  = (art.get("snippet") or "").strip()

        # 1. URL dedup
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        # 2. Snippet length
        if len(snippet) < 20:
            continue

        # 3. Recency — parse published_at
        pub_str = art.get("published_at", "")
        if pub_str:
            try:
                pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                if pub_dt < cutoff:
                    continue
            except ValueError:
                pass   # unparseable timestamp — keep article

        # 4. Exact headline dedup (case-insensitive MD5)
        h_key = hashlib.md5(headline.lower().encode()).hexdigest()
        if h_key in seen_headlines:
            continue
        seen_headlines.add(h_key)

        out.append(art)

    return out


def _pass2_semantic_dedup(articles: list[dict], openai_key: str) -> list[dict]:
    """GPT-4o semantic deduplication in batches of 25."""
    if not articles:
        return []

    kept: list[dict] = []
    batch_size = 25

    for i in range(0, len(articles), batch_size):
        batch = articles[i : i + batch_size]
        articles_text = "\n".join(
            f"[{j}] [cred:{a.get('credibility', 0.55):.2f}] {a['headline']} | {a['snippet'][:120]}"
            for j, a in enumerate(batch)
        )
        try:
            resp    = call_openai(DEDUP_PROMPT.format(articles_text=articles_text), openai_key)
            indices = extract_json(resp)
            kept.extend(batch[idx] for idx in indices if 0 <= idx < len(batch))
        except Exception as e:
            print(f"    [Agent 3] Semantic dedup failed for batch {i//batch_size}: {e} — keeping all")
            kept.extend(batch)

    return kept


def filter_agent(state: PipelineState) -> PipelineState:
    state["current_step"] = 3
    state["step_logs"].append("[Agent 3] Running Pass 1 (hard filters)...")

    after_pass1 = _pass1_hard_filter(state.get("raw_articles", []))
    state["step_logs"].append(
        f"[Agent 3] Pass 1 complete: {state['raw_article_count']} → {len(after_pass1)} articles"
    )

    state["step_logs"].append("[Agent 3] Running Pass 2 (semantic dedup via GPT-4o)...")
    after_pass2 = _pass2_semantic_dedup(after_pass1, state["openai_key"])

    state["clean_articles"]      = after_pass2
    state["clean_article_count"] = len(after_pass2)
    state["step_logs"].append(
        f"[Agent 3] ✓ Pass 2 complete: {len(after_pass1)} → {len(after_pass2)} articles retained"
    )
    return state
