"""
Agent 1b: MarketDataAgent
Fetches supplementary quantitative market context per ticker.
Runs independently of the article flow and populates state["market_context"].

Output schema per ticker:
  last_price          – Latest close price
  currency            – Trading currency (SGD, USD, etc.)
  price_change_1d     – 1-day price change %
  price_change_5d     – 5-day price change %
  volume_ratio        – Today's volume / 30-day avg volume
  analyst_rating      – Consensus rating string (Buy / Hold / Sell)
  target_price        – Consensus 12-month target price
  earnings_date       – Next earnings date (ISO 8601)
  recent_eps_actual   – Most recent reported EPS
  recent_eps_estimate – Consensus EPS estimate for that period
  fetched_at          – ISO 8601 UTC timestamp of fetch

Note: This implementation uses Yahoo Finance RSS as a free data source.
      Replace _fetch_yahoo() with a premium data provider (Alpha Vantage,
      Polygon.io, Refinitiv) for production use with real numerical data.
"""

import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils.state import PipelineState


YF_QUOTE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d"
YF_SUMMARY_URL = "https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=financialData,defaultKeyStatistics,calendarEvents,summaryDetail"


def _fetch_yahoo_chart(ticker: str) -> dict:
    """Fetch 5-day OHLCV from Yahoo Finance chart API."""
    url = YF_QUOTE_URL.format(ticker=urllib.parse.quote(ticker))
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    result = data["chart"]["result"][0]
    meta   = result["meta"]
    closes = result["indicators"]["quote"][0].get("close", [])
    volumes = result["indicators"]["quote"][0].get("volume", [])
    return {
        "last_price":      meta.get("regularMarketPrice"),
        "currency":        meta.get("currency", ""),
        "prev_close":      meta.get("previousClose") or meta.get("chartPreviousClose"),
        "closes":          [c for c in closes if c is not None],
        "volumes":         [v for v in volumes if v is not None],
        "regular_volume":  meta.get("regularMarketVolume"),
    }


def _fetch_yahoo_summary(ticker: str) -> dict:
    """Fetch analyst consensus and earnings data from Yahoo Finance quoteSummary."""
    url = YF_SUMMARY_URL.format(ticker=urllib.parse.quote(ticker))
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    result = data.get("quoteSummary", {}).get("result", [{}])[0]
    fin    = result.get("financialData", {})
    cal    = result.get("calendarEvents", {})
    return {
        "analyst_rating":      fin.get("recommendationKey", "").title() or None,
        "target_price":        fin.get("targetMeanPrice", {}).get("raw"),
        "recent_eps_actual":   fin.get("earningsPerShare", {}).get("raw"),
        "recent_eps_estimate": None,  # available via earningsTrend; omitted for simplicity
        "earnings_date":       (
            cal.get("earnings", {})
               .get("earningsDate", [{}])[0]
               .get("fmt")
        ),
    }


def _build_market_context_for_ticker(ticker: str) -> dict:
    """Build the full market context dict for one ticker. Returns empty dict on failure."""
    now = datetime.now(timezone.utc).isoformat()
    try:
        chart   = _fetch_yahoo_chart(ticker)
        summary = _fetch_yahoo_summary(ticker)

        closes  = chart["closes"]
        last    = chart["last_price"] or (closes[-1] if closes else None)
        prev    = chart["prev_close"] or (closes[-2] if len(closes) >= 2 else None)

        p1d = round((last / prev - 1) * 100, 2) if last and prev and prev != 0 else None
        p5d = round((last / closes[0] - 1) * 100, 2) if last and closes and closes[0] else None

        volumes = chart["volumes"]
        avg30   = chart["regular_volume"]
        vol_ratio = round(avg30 / (sum(volumes) / len(volumes)), 2) if volumes and avg30 else None

        return {
            "last_price":          last,
            "currency":            chart["currency"],
            "price_change_1d":     p1d,
            "price_change_5d":     p5d,
            "volume_ratio":        vol_ratio,
            "analyst_rating":      summary["analyst_rating"],
            "target_price":        summary["target_price"],
            "earnings_date":       summary["earnings_date"],
            "recent_eps_actual":   summary["recent_eps_actual"],
            "recent_eps_estimate": summary["recent_eps_estimate"],
            "fetched_at":          now,
        }
    except Exception as e:
        # Return a minimal stub so downstream agents degrade gracefully
        return {"fetched_at": now, "_error": str(e)}


def market_data_agent(state: PipelineState) -> PipelineState:
    """
    Agent 1b: fetch market context for every ticker in parallel.
    Failures are silently swallowed — market context is supplementary.
    """
    tickers = state.get("watchlist", [])
    state["step_logs"].append(f"[Agent 1b] Fetching market data for {len(tickers)} tickers...")

    market_context: dict = {}

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(_build_market_context_for_ticker, t): t for t in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            market_context[ticker] = future.result()

    state["market_context"] = market_context

    fetched = sum(1 for v in market_context.values() if not v.get("_error"))
    failed  = len(market_context) - fetched
    msg     = f"[Agent 1b] ✓ Market data fetched for {fetched}/{len(tickers)} tickers"
    if failed:
        msg += f" ({failed} failed — will use article-only signals)"
    state["step_logs"].append(msg)
    return state
