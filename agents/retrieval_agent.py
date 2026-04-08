"""
agents/retrieval_agent.py
-------------------------
Agent 2 — NewsRetrievalAgent
"""

from __future__ import annotations

import re
import html
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

from core.base_agent import BaseAgent
from core.state import PipelineState
from utils.llm import extract_json  # Updated import to match your project structure

# ── Credibility tiers ─────────────────────────────────────────────────────────
SOURCE_CREDIBILITY: dict[str, float] = {
    "sgx": 1.00, "mas": 1.00,
    "reuters": 0.85, "bloomberg": 0.85,
    "business times": 0.85, "straits times": 0.85,
    "ft.com": 0.85, "financial times": 0.85,
    "wsj": 0.85, "wall street": 0.85,
    "cnbc": 0.70, "cna": 0.70, "nikkei": 0.70,
    "barron": 0.70, "marketwatch": 0.70, "seeking alpha": 0.70,
    "yahoo": 0.55, "finviz": 0.55, "benzinga": 0.55,
    "motley fool": 0.55, "investing.com": 0.55,
}
DEFAULT_CRED = 0.55
 
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "en-US,en;q=0.9",
}
 
REUTERS_FEEDS = {
    "business":   "https://feeds.reuters.com/reuters/businessNews",
    "markets":    "https://feeds.reuters.com/reuters/companyNews",
    "technology": "https://feeds.reuters.com/reuters/technologyNews",
}
 
class NewsRetrievalAgent(BaseAgent):
    """
    Agent 2: Parallel multi-source RSS/HTML news fetcher.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.simulation_mode = config.get("simulation_mode", True)

    # ── public entry point ────────────────────────────────────────────────────
    def run(self, state: PipelineState) -> PipelineState:
        # 1. Use dot notation for PipelineState dataclass
        bundles = state.query_bundles
        
        self.log_start(f"Fetching from 5 sources for {len(bundles)} tickers")
        
        # 2. Update state attributes directly
        state.current_step = 2
        state.step_logs.append(
            f"[Agent 2] Fetching from Yahoo Finance RSS, Google News RSS, "
            f"Reuters RSS, Finviz, Seeking Alpha for {len(bundles)} tickers..."
        )
        if self.simulation_mode:
            with open("retrieval_test_output.json", "r",  encoding='utf-8') as f:
                data = extract_json(f.read())
                state = PipelineState(**data)
                msg = f"[Agent 2] ✓ {len(state.raw_articles)} articles (simulated)"
                state.step_logs.append(msg)
                self.log_done(msg)
                
                return state
        else:
            seen_urls:    set[str]   = set()
            all_articles: list[dict] = []

            # Optimization: Parallelize fetching across all bundles (tickers)
            with ThreadPoolExecutor(max_workers=min(len(bundles) * 6, 12)) as ex:
                futures = {ex.submit(self._fetch_bundle, b): b for b in bundles}
                for future in as_completed(futures):
                    try:
                        for art in future.result():
                            if art["url"] not in seen_urls:
                                seen_urls.add(art["url"])
                                all_articles.append(art)
                    except Exception as e:
                        # Access bundle dictionary key safely
                        ticker = futures[future].get("ticker", "?")
                        self.logger.warning(f"Bundle fetch error ({ticker}): {e}")

            # Sort by date (newest first)
            all_articles.sort(key=lambda a: a.get("published_at", ""), reverse=True)

            # Generate summary for logging
            source_counts: dict[str, int] = {}
            for art in all_articles:
                source_counts[art["source"]] = source_counts.get(art["source"], 0) + 1
            
            summary = ", ".join(
                f"{s}: {n}"
                for s, n in sorted(source_counts.items(), key=lambda x: -x[1])
            )

        # 3. Save to state using dot notation
        state.raw_articles = all_articles
        state.raw_article_count = len(all_articles)
        
        msg = f"[Agent 2] ✓ {len(all_articles)} articles ({summary})"
        state.step_logs.append(msg)
        self.log_done(msg)
        
        return state


    # ... [Internal helper methods _fetch_bundle, _get, _clean, etc. remain the same] ...
    # ── per-bundle orchestration ──────────────────────────────────────────────
    def _fetch_bundle(self, bundle: dict) -> list[dict]:
        ticker  = bundle.get("ticker", "UNKNOWN")
        company = bundle.get("company_name", ticker)
        results: list[dict] = []
 
        results += self._yahoo_rss(ticker, company)
        results += self._seeking_alpha_rss(ticker, company)
        results += self._finviz(ticker, company)
        results += self._reuters_rss(ticker, company)
 
        for q in bundle.get("company_queries", [])[:3]:
            results += self._google_news_rss(q, "company", ticker, company)
        for q in bundle.get("industry_queries", [])[:2]:
            results += self._google_news_rss(q, "industry", ticker, company)
 
        return results
 
    # ── HTTP helpers ──────────────────────────────────────────────────────────
    @staticmethod
    def _get(url: str, timeout: int = 12) -> bytes:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
 
    @staticmethod
    def _clean(text: str) -> str:
        text = html.unescape(text or "")
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()
 
    @staticmethod
    def _parse_date(date_str: str) -> str:
        for fmt in (
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S GMT",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%SZ",
        ):
            try:
                dt = datetime.strptime((date_str or "").strip(), fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc).isoformat()
            except ValueError:
                continue
        return date_str or ""
 
    def _normalise(
        self, headline: str, snippet: str, url: str, source: str,
        published_at: str, query_type: str, ticker: str, company: str, raw: dict,
    ) -> dict | None:
        url      = (url or "").strip()
        headline = self._clean(headline)
        if not url or not headline:
            return None
        sl = source.lower()
        cred = next((v for k, v in SOURCE_CREDIBILITY.items() if k in sl), DEFAULT_CRED)
        return {
            "ticker": ticker, "company": company,
            "headline": headline, "snippet": self._clean(snippet),
            "url": url, "source": source,
            "published_at": self._parse_date(published_at),
            "query_type": query_type, "credibility": cred, "raw": raw,
        }
 
    # ── Source fetchers ───────────────────────────────────────────────────────
    def _yahoo_rss(self, ticker: str, company: str) -> list[dict]:
        url = ("https://feeds.finance.yahoo.com/rss/2.0/headline?"
               + urllib.parse.urlencode({"s": ticker, "region": "US", "lang": "en-US"}))
        try:
            root = ET.fromstring(self._get(url))
            return [a for item in root.findall(".//item")[:15]
                    if (a := self._normalise(
                        item.findtext("title",""), item.findtext("description",""),
                        item.findtext("link",""), "Yahoo Finance",
                        item.findtext("pubDate",""), "company", ticker, company,
                        {"feed": "yahoo_finance_rss"},
                    )) is not None]
        except Exception as e:
            self.logger.debug(f"Yahoo RSS failed ({ticker}): {e}")
            return []
 
    def _google_news_rss(self, query: str, query_type: str, ticker: str, company: str) -> list[dict]:
        url = ("https://news.google.com/rss/search?"
               + urllib.parse.urlencode({"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}))
        try:
            root  = ET.fromstring(self._get(url))
            items = root.findall(".//item")
            results = []
            for item in items[:12]:
                src_el = item.find("source")
                src    = src_el.text if src_el is not None else "Google News"
                art = self._normalise(
                    item.findtext("title",""), item.findtext("description",""),
                    item.findtext("link",""), src,
                    item.findtext("pubDate",""), query_type, ticker, company,
                    {"feed": "google_news_rss", "query": query},
                )
                if art:
                    results.append(art)
            return results
        except Exception as e:
            self.logger.debug(f"Google News RSS failed ({query!r}): {e}")
            return []
 
    def _reuters_rss(self, ticker: str, company: str) -> list[dict]:
        keywords = {ticker.lower(), company.lower().split()[0]}
        results  = []
        for feed_name, feed_url in REUTERS_FEEDS.items():
            try:
                root = ET.fromstring(self._get(feed_url))
                for item in root.findall(".//item")[:30]:
                    title = item.findtext("title","")
                    desc  = item.findtext("description","")
                    if not any(kw in (title + " " + desc).lower() for kw in keywords):
                        continue
                    art = self._normalise(
                        title, desc, item.findtext("link",""), "Reuters",
                        item.findtext("pubDate",""), "company", ticker, company,
                        {"feed": f"reuters_{feed_name}"},
                    )
                    if art:
                        results.append(art)
            except Exception as e:
                self.logger.debug(f"Reuters RSS ({feed_name}) failed: {e}")
        return results
 
    def _finviz(self, ticker: str, company: str) -> list[dict]:
        url = f"https://finviz.com/quote.ashx?t={urllib.parse.quote(ticker)}"
        try:
            raw_html = self._get(url).decode("utf-8", errors="ignore")
            pattern  = re.compile(
                r'<a[^>]+class="news-link"[^>]+href="([^"]+)"[^>]*>([^<]+)</a>'
                r'.*?<td[^>]*>(\w+\s+\d+[^<]*)</td>', re.DOTALL,
            )
            results = []
            for m in pattern.finditer(raw_html):
                art = self._normalise(
                    m.group(2), "", m.group(1), "Finviz",
                    m.group(3), "company", ticker, company,
                    {"feed": "finviz"},
                )
                if art:
                    results.append(art)
                if len(results) >= 10:
                    break
            return results
        except Exception as e:
            self.logger.debug(f"Finviz failed ({ticker}): {e}")
            return []
 
    def _seeking_alpha_rss(self, ticker: str, company: str) -> list[dict]:
        url = f"https://seekingalpha.com/api/sa/combined/{urllib.parse.quote(ticker)}.xml"
        try:
            root = ET.fromstring(self._get(url))
            return [a for item in root.findall(".//item")[:10]
                    if (a := self._normalise(
                        item.findtext("title",""), item.findtext("description",""),
                        item.findtext("link",""), "Seeking Alpha",
                        item.findtext("pubDate",""), "company", ticker, company,
                        {"feed": "seeking_alpha_rss"},
                    )) is not None]
        except Exception as e:
            self.logger.debug(f"Seeking Alpha RSS failed ({ticker}): {e}")
            return []

# ── LangGraph node wrapper ─────────────────────────────────────────────────────
def retrieval_agent(state: PipelineState) -> PipelineState:
    """
    LangGraph node wrapper for the Retrieval Agent.
    """
    # No API keys required for this agent as per your docstring
    agent = NewsRetrievalAgent({})
    return agent.run(state)