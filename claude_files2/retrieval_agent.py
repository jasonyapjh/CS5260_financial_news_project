"""
Agent 2: NewsRetrievalAgent  — NO API KEY REQUIRED
Fetches articles from 5 free sources in parallel using only RSS feeds
and public JSON endpoints.

Sources:
  1. Yahoo Finance RSS       – per-ticker headlines       (query_type: company)
  2. Google News RSS         – company + industry search  (query_type: company / industry)
  3. Reuters RSS             – business / markets feed    (query_type: macro)
  4. Finviz                  – per-ticker news scrape      (query_type: company)
  5. Seeking Alpha RSS       – per-ticker news feed        (query_type: company)

All articles are normalised to the canonical schema:
  ticker, company, headline, snippet, url, source,
  published_at, query_type, credibility, raw
"""

import re
import html
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

from utils.state import PipelineState


# ── Credibility tiers ─────────────────────────────────────────────────────────
SOURCE_CREDIBILITY: dict[str, float] = {
    # Tier 1
    "sgx":              1.00,
    "mas":              1.00,
    # Tier 2
    "reuters":          0.85,
    "bloomberg":        0.85,
    "business times":   0.85,
    "straits times":    0.85,
    "ft.com":           0.85,
    "financial times":  0.85,
    "wsj":              0.85,
    "wall street":      0.85,
    # Tier 3
    "cnbc":             0.70,
    "cna":              0.70,
    "nikkei":           0.70,
    "barron":           0.70,
    "marketwatch":      0.70,
    "seeking alpha":    0.70,
    # Tier 4
    "yahoo":            0.55,
    "finviz":           0.55,
    "benzinga":         0.55,
    "motley fool":      0.55,
    "investing.com":    0.55,
}
DEFAULT_CRED = 0.55


def _credibility(source_name: str) -> float:
    sl = source_name.lower()
    for key, score in SOURCE_CREDIBILITY.items():
        if key in sl:
            return score
    return DEFAULT_CRED


# ── Shared HTTP helper ─────────────────────────────────────────────────────────
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


def _get(url: str, timeout: int = 12) -> bytes:
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _clean(text: str) -> str:
    """Strip HTML tags and decode entities."""
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_rss_date(date_str: str) -> str:
    """Parse RSS pubDate → ISO 8601 UTC. Returns empty string on failure."""
    if not date_str:
        return ""
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S GMT",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
    ):
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except ValueError:
            continue
    return date_str


def _normalise(
    headline: str,
    snippet: str,
    url: str,
    source: str,
    published_at: str,
    query_type: str,
    ticker: str,
    company: str,
    raw: dict,
) -> dict | None:
    url = (url or "").strip()
    headline = _clean(headline)
    if not url or not headline:
        return None
    return {
        "ticker":       ticker,
        "company":      company,
        "headline":     headline,
        "snippet":      _clean(snippet),
        "url":          url,
        "source":       source,
        "published_at": _parse_rss_date(published_at),
        "query_type":   query_type,
        "credibility":  _credibility(source),
        "raw":          raw,
    }


# ── Source 1: Yahoo Finance RSS ───────────────────────────────────────────────
def _fetch_yahoo_finance_rss(ticker: str, company: str) -> list[dict]:
    """
    Yahoo Finance news RSS feed for a specific ticker.
    URL: https://feeds.finance.yahoo.com/rss/2.0/headline?s=TICKER&region=US&lang=en-US
    """
    url = (
        "https://feeds.finance.yahoo.com/rss/2.0/headline?"
        + urllib.parse.urlencode({"s": ticker, "region": "US", "lang": "en-US"})
    )
    try:
        root = ET.fromstring(_get(url))
        items = root.findall(".//item")
        results = []
        for item in items[:15]:
            art = _normalise(
                headline    = item.findtext("title", ""),
                snippet     = item.findtext("description", ""),
                url         = item.findtext("link", ""),
                source      = "Yahoo Finance",
                published_at= item.findtext("pubDate", ""),
                query_type  = "company",
                ticker      = ticker,
                company     = company,
                raw         = {"feed": "yahoo_finance_rss"},
            )
            if art:
                results.append(art)
        return results
    except Exception as e:
        print(f"    [Agent 2] Yahoo Finance RSS failed ({ticker}): {e}")
        return []


# ── Source 2: Google News RSS ─────────────────────────────────────────────────
def _fetch_google_news_rss(query: str, query_type: str, ticker: str, company: str) -> list[dict]:
    """
    Google News RSS search — no API key needed.
    URL: https://news.google.com/rss/search?q=QUERY&hl=en-US&gl=US&ceid=US:en
    """
    url = (
        "https://news.google.com/rss/search?"
        + urllib.parse.urlencode({
            "q":    query,
            "hl":   "en-US",
            "gl":   "US",
            "ceid": "US:en",
        })
    )
    try:
        root  = ET.fromstring(_get(url))
        ns    = {"media": "http://search.yahoo.com/mrss/"}
        items = root.findall(".//item")
        results = []
        for item in items[:12]:
            # Google News URLs are redirect wrappers — extract the source name
            # from the <source> tag when available
            source_el   = item.find("source")
            source_name = source_el.text if source_el is not None else "Google News"

            art = _normalise(
                headline    = item.findtext("title", ""),
                snippet     = item.findtext("description", ""),
                url         = item.findtext("link", ""),
                source      = source_name,
                published_at= item.findtext("pubDate", ""),
                query_type  = query_type,
                ticker      = ticker,
                company     = company,
                raw         = {"feed": "google_news_rss", "query": query},
            )
            if art:
                results.append(art)
        return results
    except Exception as e:
        print(f"    [Agent 2] Google News RSS failed ({query!r}): {e}")
        return []


# ── Source 3: Reuters RSS ─────────────────────────────────────────────────────
# Reuters provides public RSS feeds for their top sections.
REUTERS_FEEDS = {
    "business":  "https://feeds.reuters.com/reuters/businessNews",
    "markets":   "https://feeds.reuters.com/reuters/companyNews",
    "technology":"https://feeds.reuters.com/reuters/technologyNews",
}


def _fetch_reuters_rss(ticker: str, company: str) -> list[dict]:
    """Fetch Reuters business + markets RSS and keep articles mentioning company/ticker."""
    results = []
    keywords = {ticker.lower(), company.lower().split()[0]}  # e.g. {"aapl", "apple"}

    for feed_name, feed_url in REUTERS_FEEDS.items():
        try:
            root  = ET.fromstring(_get(feed_url))
            items = root.findall(".//item")
            for item in items[:30]:
                title   = item.findtext("title", "")
                desc    = item.findtext("description", "")
                text    = (title + " " + desc).lower()
                if not any(kw in text for kw in keywords):
                    continue
                art = _normalise(
                    headline    = title,
                    snippet     = desc,
                    url         = item.findtext("link", ""),
                    source      = "Reuters",
                    published_at= item.findtext("pubDate", ""),
                    query_type  = "company",
                    ticker      = ticker,
                    company     = company,
                    raw         = {"feed": f"reuters_{feed_name}"},
                )
                if art:
                    results.append(art)
        except Exception as e:
            print(f"    [Agent 2] Reuters RSS ({feed_name}) failed: {e}")

    return results


# ── Source 4: Finviz news ─────────────────────────────────────────────────────
def _fetch_finviz(ticker: str, company: str) -> list[dict]:
    """
    Scrape Finviz ticker news table (plain HTML, no JS).
    URL: https://finviz.com/quote.ashx?t=TICKER
    """
    url = f"https://finviz.com/quote.ashx?t={urllib.parse.quote(ticker)}"
    try:
        raw_html = _get(url).decode("utf-8", errors="ignore")
        # Finviz news rows: <a ...>headline</a> in a table with class "news-link"
        pattern = re.compile(
            r'<a[^>]+class="news-link"[^>]+href="([^"]+)"[^>]*>([^<]+)</a>'
            r'.*?<td[^>]*>(\w+\s+\d+[^<]*)</td>',
            re.DOTALL,
        )
        results = []
        for m in pattern.finditer(raw_html):
            article_url, headline, date_str = m.group(1), m.group(2), m.group(3)
            art = _normalise(
                headline    = headline,
                snippet     = "",
                url         = article_url,
                source      = "Finviz",
                published_at= date_str,
                query_type  = "company",
                ticker      = ticker,
                company     = company,
                raw         = {"feed": "finviz"},
            )
            if art:
                results.append(art)
            if len(results) >= 10:
                break
        return results
    except Exception as e:
        print(f"    [Agent 2] Finviz failed ({ticker}): {e}")
        return []


# ── Source 5: Seeking Alpha RSS ───────────────────────────────────────────────
def _fetch_seeking_alpha_rss(ticker: str, company: str) -> list[dict]:
    """
    Seeking Alpha provides public RSS per ticker.
    URL: https://seekingalpha.com/api/sa/combined/{TICKER}.xml
    """
    url = f"https://seekingalpha.com/api/sa/combined/{urllib.parse.quote(ticker)}.xml"
    try:
        root  = ET.fromstring(_get(url))
        items = root.findall(".//item")
        results = []
        for item in items[:10]:
            art = _normalise(
                headline    = item.findtext("title", ""),
                snippet     = item.findtext("description", ""),
                url         = item.findtext("link", ""),
                source      = "Seeking Alpha",
                published_at= item.findtext("pubDate", ""),
                query_type  = "company",
                ticker      = ticker,
                company     = company,
                raw         = {"feed": "seeking_alpha_rss"},
            )
            if art:
                results.append(art)
        return results
    except Exception as e:
        print(f"    [Agent 2] Seeking Alpha RSS failed ({ticker}): {e}")
        return []


# ── Orchestrator ──────────────────────────────────────────────────────────────
def _fetch_all_for_bundle(bundle: dict) -> list[dict]:
    """Fetch from all 5 sources for one query bundle. Returns list of articles."""
    ticker  = bundle.get("ticker", "UNKNOWN")
    company = bundle.get("company_name", ticker)
    results: list[dict] = []

    # Per-ticker sources (always run)
    results += _fetch_yahoo_finance_rss(ticker, company)
    results += _fetch_seeking_alpha_rss(ticker, company)
    results += _fetch_finviz(ticker, company)
    results += _fetch_reuters_rss(ticker, company)

    # Google News — company queries + industry queries
    for q in bundle.get("company_queries", [])[:3]:    # cap at 3 to avoid rate-limiting
        results += _fetch_google_news_rss(q, "company", ticker, company)
    for q in bundle.get("industry_queries", [])[:2]:
        results += _fetch_google_news_rss(q, "industry", ticker, company)

    return results


def retrieval_agent(state: PipelineState) -> PipelineState:
    state["current_step"] = 2
    bundles = state.get("query_bundles", [])
    state["step_logs"].append(
        f"[Agent 2] Fetching from Yahoo Finance RSS, Google News RSS, Reuters RSS, "
        f"Finviz, Seeking Alpha for {len(bundles)} tickers..."
    )

    seen_urls:    set[str]  = set()
    all_articles: list[dict] = []

    # Fetch all bundles in parallel
    with ThreadPoolExecutor(max_workers=min(len(bundles) * 6, 12)) as executor:
        futures = {executor.submit(_fetch_all_for_bundle, b): b for b in bundles}
        for future in as_completed(futures):
            try:
                for art in future.result():
                    if art["url"] not in seen_urls:
                        seen_urls.add(art["url"])
                        all_articles.append(art)
            except Exception as e:
                ticker = futures[future].get("ticker", "?")
                print(f"    [Agent 2] Bundle fetch error ({ticker}): {e}")

    # Sort newest first
    all_articles.sort(key=lambda a: a.get("published_at", ""), reverse=True)

    # Count by source for logging
    source_counts: dict[str, int] = {}
    for art in all_articles:
        src = art["source"]
        source_counts[src] = source_counts.get(src, 0) + 1

    source_summary = ", ".join(
        f"{src}: {n}" for src, n in sorted(source_counts.items(), key=lambda x: -x[1])
    )

    state["raw_articles"]      = all_articles
    state["raw_article_count"] = len(all_articles)
    state["step_logs"].append(
        f"[Agent 2] ✓ Retrieved {len(all_articles)} raw articles "
        f"({source_summary})"
    )
    return state
