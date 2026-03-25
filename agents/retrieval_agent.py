"""
Agent 2: News Retrieval Agent
================================
Input  : List of QueryBundles from Agent 1
Output : Per-ticker raw article sets + parallel industry article stream

Strategy
--------
Multiple public sources are queried:
  1. Yahoo Finance RSS feed (per ticker)
  2. Google News RSS (via query string)
  3. Finviz news scraper (per ticker)
  4. yfinance .news attribute

Articles are deduplicated by URL at this stage and enriched with metadata
(source, timestamp, headline, snippet).
"""

import hashlib
import time
import re
import feedparser
import requests
from typing import List, Dict
from datetime import datetime, timezone

from utils.models import QueryBundle, Article

@dataclass
class QueryBundle:
    """Output of Agent 1: Watchlist & Context Agent."""
    ticker: str
    company_name: str
    aliases: List[str]
    sector: str
    industry: str
    company_queries: List[str]   # company-specific search queries
    industry_queries: List[str]  # broader industry/macro queries
@dataclass
class Article:
    """A single retrieved news article."""
    id: str
    ticker: str
    title: str
    url: str
    source: str
    published: Optional[str]
    snippet: str
    query_used: str
    is_industry: bool = False  # True if retrieved via industry query

# ---------------------------------------------------------------------------
# Source helpers
# ---------------------------------------------------------------------------

def _make_id(url: str, ticker: str) -> str:
    """Stable short ID from URL hash."""
    return ticker + "_" + hashlib.md5(url.encode()).hexdigest()[:8]


def _fetch_yahoo_rss(ticker: str) -> List[Article]:
    """Fetch articles from Yahoo Finance RSS for a given ticker."""
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
    articles = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:15]:
            article = Article(
                id=_make_id(entry.get("link", ""), ticker),
                ticker=ticker,
                title=entry.get("title", ""),
                url=entry.get("link", ""),
                source="Yahoo Finance",
                published=entry.get("published", ""),
                snippet=entry.get("summary", "")[:500],
                query_used=f"Yahoo RSS: {ticker}",
                is_industry=False,
            )
            articles.append(article)
    except Exception as e:
        print(f"    [Agent 2] Yahoo RSS error for {ticker}: {e}")
    return articles


def _fetch_google_news_rss(query: str, ticker: str, is_industry: bool = False) -> List[Article]:
    """Fetch articles from Google News RSS for a search query."""
    encoded = requests.utils.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
    articles = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:10]:
            article = Article(
                id=_make_id(entry.get("link", ""), ticker),
                ticker=ticker,
                title=entry.get("title", ""),
                url=entry.get("link", ""),
                source=entry.get("source", {}).get("title", "Google News") if hasattr(entry.get("source", ""), "get") else "Google News",
                published=entry.get("published", ""),
                snippet=entry.get("summary", "")[:500],
                query_used=query,
                is_industry=is_industry,
            )
            articles.append(article)
    except Exception as e:
        print(f"    [Agent 2] Google News RSS error for '{query}': {e}")
    return articles


def _fetch_yfinance_news(ticker: str) -> List[Article]:
    """Fetch news from yfinance .news attribute."""
    import yfinance as yf
    articles = []
    try:
        news_items = yf.Ticker(ticker).news or []
        for item in news_items[:15]:
            content = item.get("content", {})
            title = content.get("title", item.get("title", ""))
            url = content.get("canonicalUrl", {}).get("url", "") if isinstance(content.get("canonicalUrl"), dict) else item.get("link", "")
            summary = content.get("summary", item.get("summary", ""))
            pub_date = content.get("pubDate", "")
            provider = content.get("provider", {})
            source_name = provider.get("displayName", "Yahoo Finance") if isinstance(provider, dict) else "Yahoo Finance"

            if not url:
                continue

            article = Article(
                id=_make_id(url, ticker),
                ticker=ticker,
                title=title,
                url=url,
                source=source_name,
                published=pub_date,
                snippet=summary[:500] if summary else "",
                query_used=f"yfinance: {ticker}",
                is_industry=False,
            )
            articles.append(article)
    except Exception as e:
        print(f"    [Agent 2] yfinance news error for {ticker}: {e}")
    return articles


# ---------------------------------------------------------------------------
# Main agent function
# ---------------------------------------------------------------------------

def run(query_bundles: List[QueryBundle]) -> Dict[str, List[Article]]:
    """
    Retrieve news articles for each ticker in the query bundles.

    Parameters
    ----------
    query_bundles : list of QueryBundle

    Returns
    -------
    dict mapping ticker -> list of Article
        Articles include both company-specific and industry-level items.
        Industry articles have is_industry=True.
    """
    results: Dict[str, List[Article]] = {}

    for bundle in query_bundles:
        ticker = bundle.ticker
        print(f"  [Agent 2] Retrieving news for: {ticker} ({bundle.company_name})")
        seen_urls: set = set()
        articles: List[Article] = []

        def add_articles(new_articles: List[Article]):
            for a in new_articles:
                if a.url and a.url not in seen_urls and a.title:
                    seen_urls.add(a.url)
                    articles.append(a)

        # Source 1: Yahoo Finance RSS
        add_articles(_fetch_yahoo_rss(ticker))
        time.sleep(0.3)

        # Source 2: yfinance .news
        add_articles(_fetch_yfinance_news(ticker))
        time.sleep(0.3)

        # Source 3: Google News RSS for company queries
        for query in bundle.company_queries[:4]:
            add_articles(_fetch_google_news_rss(query, ticker, is_industry=False))
            time.sleep(0.4)

        # Source 4: Google News RSS for industry queries
        for query in bundle.industry_queries[:3]:
            add_articles(_fetch_google_news_rss(query, ticker, is_industry=True))
            time.sleep(0.4)

        results[ticker] = articles
        print(f"    [Agent 2] Retrieved {len(articles)} unique articles for {ticker}")

    return results
