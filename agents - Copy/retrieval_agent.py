import feedparser
import yfinance as yf
import urllib.request
import urllib.parse
from datetime import datetime
from utils.state import PipelineState
import json
def retrieval_agent(state: PipelineState) -> PipelineState:
    state["current_step"] = 2
    state["step_logs"].append("[Agent 2] Retrieving news from YF, Google, Finviz, and yfinance...")

    seen, articles = set(), []

    # for bundle in state.get("query_bundles", []):
    #     ticker = bundle["ticker"]
    #     company_name = bundle.get("company_name", ticker)
    #     industry = bundle.get("industry", "")

    #     # --- 1. Yahoo Finance RSS (Ticker Based) ---
    #     yf_rss = f"https://finance.yahoo.com/rss/headline?s={ticker}"
    #     feed = feedparser.parse(yf_rss)
    #     for entry in feed.entries:
    #         _add_article(articles, seen, entry, ticker, company_name, industry, "Yahoo Finance RSS")

    #     # --- 2. Google News RSS (Query Based) ---
    #     for q in bundle.get("company_queries", [])[:2]: # Top 2 queries to avoid bloat
    #         encoded_q = urllib.parse.quote(q)
    #         g_rss = f"https://news.google.com/rss/search?q={encoded_q}&hl=en-US&gl=US&ceid=US:en"
    #         g_feed = feedparser.parse(g_rss)
    #         for entry in g_feed.entries:
    #             _add_article(articles, seen, entry, ticker, company_name, industry, "Google News")

    #     # --- 3. Finviz Scraper (Ticker Based) ---
    #     # Note: Finviz often requires a User-Agent to prevent 403 errors
    #     try:
    #         fv_url = f"https://finviz.com/quote.ashx?t={ticker}"
    #         req = urllib.request.Request(fv_url, headers={'User-Agent': 'Mozilla/5.0'})
    #         with urllib.request.urlopen(req, timeout=10) as r:
    #             html = r.read().decode('utf-8')
    #             # Simple extraction for demo; for production, use BeautifulSoup
    #             if "news-table" in html:
    #                 state["step_logs"].append(f"[Agent 2] Scraped Finviz for {ticker}")
    #     except Exception as e:
    #         state["step_logs"].append(f"[Agent 2] Finviz fail for {ticker}: {e}")

    #     # --- 4. yfinance .news attribute ---
    #     try:
    #         ticker_obj = yf.Ticker(ticker)
    #         for news_item in ticker_obj.news:
    #             url = news_item.get("link", "")
    #             if url not in seen:
    #                 seen.add(url)
    #                 articles.append({
    #                     "ticker": ticker,
    #                     "company_name": company_name,
    #                     "industry": industry,
    #                     "headline": news_item.get("title", ""),
    #                     "snippet": "", # yfinance news doesn't always provide snippets
    #                     "content_preview": "",
    #                     "source": news_item.get("publisher", "yfinance"),
    #                     "url": url,
    #                     "published_at": str(datetime.fromtimestamp(news_item.get("providerPublishTime", 0))),
    #                 })
    #     except Exception:
    #         pass

    # output_path = "agent_2_output.json"
    # with open(output_path, "w") as f:
    #    json.dump(articles, f, indent=4)

    with open("agent_2_output.json", "r") as f:
        articles = json.load(f)

    state["raw_articles"] = articles
    state["raw_article_count"] = len(articles)
    state["step_logs"].append(f"[Agent 2] ✓ Total {len(articles)} articles retrieved")
    return state

def _add_article(articles, seen, entry, ticker, company_name, industry, source_name):
    url = entry.get("link", "")
    if url and url not in seen:
        seen.add(url)
        articles.append({
            "ticker": ticker,
            "company_name": company_name,
            "industry": industry,
            "headline": entry.get("title", ""),
            "snippet": entry.get("summary", "") or "",
            "content_preview": "",
            "source": source_name,
            "url": url,
            "published_at": entry.get("published", ""),
        })