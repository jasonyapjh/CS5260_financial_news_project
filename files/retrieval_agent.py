"""
Agent 2: NewsRetrievalAgent
Fetches articles from multiple sources in parallel and normalises them
to the canonical article schema defined in the data flow spec.

Canonical article schema:
  ticker       – SGX/stock ticker or "MACRO"
  company      – Full company name
  headline     – Article title
  snippet      – Short description or excerpt
  url          – Canonical article URL
  source       – Data source name (e.g. "SGX Announcements", "Reuters")
  published_at – ISO 8601 UTC timestamp
  query_type   – "company" | "industry" | "macro" | "sentiment"
  raw          – Original API response dict (for debugging)
"""

import json
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

from utils.state import PipelineState


NEWSAPI_BASE = "https://newsapi.org/v2/everything"

# Source credibility tiers (used downstream by Agent 6)
SOURCE_CREDIBILITY = {
    # Tier 1
    "SGX Announcements": 1.00,
    "MAS":               1.00,
    # Tier 2
    "Business Times":    0.85,
    "Straits Times":     0.85,
    "Reuters":           0.85,
    "Bloomberg":         0.85,
    # Tier 3
    "CNA":               0.70,
    "Nikkei Asia":       0.70,
    "CNBC":              0.70,
    # Tier 4 (default for unknown sources)
    "Yahoo Finance":     0.55,
    "Singapore Business Review": 0.55,
}
DEFAULT_CREDIBILITY = 0.55


def _credibility(source_name: str) -> float:
    """Return credibility score for a source name (partial match)."""
    for key, score in SOURCE_CREDIBILITY.items():
        if key.lower() in source_name.lower():
            return score
    return DEFAULT_CREDIBILITY


def _fetch_newsapi(
    query: str,
    api_key: str,
    from_date: str,
    query_type: str,
    ticker: str,
    company: str,
) -> list[dict]:
    """Fetch up to 10 articles from NewsAPI and normalise to canonical schema."""
    params = urllib.parse.urlencode({
        "q":        query,
        "from":     from_date,
        "sortBy":   "publishedAt",
        "language": "en",
        "pageSize": 10,
        "apiKey":   api_key,
    })
    try:
        req = urllib.request.Request(
            f"{NEWSAPI_BASE}?{params}",
            headers={"User-Agent": "FinTel/2.0"},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            raw_articles = json.loads(r.read()).get("articles", [])
    except Exception as e:
        print(f"    [Agent 2] NewsAPI warn ({query!r}): {e}")
        return []

    normalised = []
    for art in raw_articles:
        url = (art.get("url") or "").strip()
        if not url:
            continue
        source_name = art.get("source", {}).get("name", "Unknown")
        published = art.get("publishedAt", "")
        normalised.append({
            "ticker":       ticker,
            "company":      company,
            "headline":     (art.get("title") or "").strip(),
            "snippet":      (art.get("description") or "").strip(),
            "url":          url,
            "source":       source_name,
            "published_at": published,
            "query_type":   query_type,          # "company" | "industry" | "macro"
            "credibility":  _credibility(source_name),
            "raw":          art,                  # keep original for debugging
        })
    return normalised


def retrieval_agent(state: PipelineState) -> PipelineState:
    state["current_step"] = 2
    state["step_logs"].append("[Agent 2] Retrieving articles from NewsAPI...")

    from_date = (
        datetime.now(timezone.utc) - timedelta(days=7)
    ).strftime("%Y-%m-%d")

    # Build fetch tasks: (query, query_type, ticker, company)
    tasks: list[tuple[str, str, str, str]] = []
    for bundle in state.get("query_bundles", []):
        ticker  = bundle.get("ticker", "UNKNOWN")
        company = bundle.get("company_name", ticker)
        for q in bundle.get("company_queries", []):
            tasks.append((q, "company", ticker, company))
        for q in bundle.get("industry_queries", []):
            tasks.append((q, "industry", ticker, company))

    # Fetch in parallel (up to 8 workers)
    seen_urls: set[str] = set()
    all_articles: list[dict] = []

    def fetch_task(task):
        query, query_type, ticker, company = task
        return _fetch_newsapi(
            query, state["newsapi_key"], from_date, query_type, ticker, company
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_task, t): t for t in tasks}
        for future in as_completed(futures):
            for art in future.result():
                if art["url"] not in seen_urls:
                    seen_urls.add(art["url"])
                    all_articles.append(art)

    # Sort newest first
    all_articles.sort(key=lambda a: a.get("published_at", ""), reverse=True)

    state["raw_articles"]      = all_articles
    state["raw_article_count"] = len(all_articles)
    state["step_logs"].append(
        f"[Agent 2] ✓ Retrieved {len(all_articles)} raw articles "
        f"from {len(tasks)} queries across {len(state.get('query_bundles', []))} tickers"
    )
    return state
