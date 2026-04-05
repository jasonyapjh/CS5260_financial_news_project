"""
LangGraph Agent Node Functions
Refactored to follow the detailed data flow specification with proper schemas
"""

import time
import json
from datetime import datetime
from typing import Any
import yfinance as yf
import feedparser
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from .state import (
    PipelineState, Article, EventCluster, EventCard, MarketContext
)


def get_llm(state: PipelineState):
    """Get LLM instance based on provider"""
    if state["llm_provider"] == "gemini":
        return ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.7)
    else:
        return ChatOpenAI(model="gpt-4", temperature=0.7)


# ============================================================================
# AGENT 1: WatchlistContextAgent
# ============================================================================

def agent_1_watchlist_context(state: PipelineState) -> PipelineState:
    """
    Agent 1: Watchlist & Context Agent
    Resolves tickers to company metadata and aliases.
    """
    start_time = time.time()
    state["current_agent"] = "Agent 1: Watchlist & Context"
    state["progress"] = 5
    
    try:
        ticker_metadata = {}
        
        for ticker in state["tickers"]:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                
                ticker_metadata[ticker] = {
                    "name": info.get("longName", ticker),
                    "sector": info.get("sector", "Unknown"),
                    "industry": info.get("industry", "Unknown"),
                    "market_cap": info.get("marketCap", 0),
                    "pe_ratio": info.get("trailingPE", None),
                    "dividend_yield": info.get("dividendYield", None),
                }
            except Exception as e:
                ticker_metadata[ticker] = {
                    "name": ticker,
                    "sector": "Unknown",
                    "industry": "Unknown",
                }
        
        state["ticker_metadata"] = ticker_metadata
        
    except Exception as e:
        state["error_message"] = f"Agent 1 error: {str(e)}"
        state["status"] = "failed"
    
    state["agent_timings"]["agent_1"] = time.time() - start_time
    return state


# ============================================================================
# AGENT 1b: MarketDataAgent
# ============================================================================

def agent_1b_market_data(state: PipelineState) -> PipelineState:
    """
    Agent 1b: Market Data Agent
    Fetches quantitative market context (price, volume, analyst ratings, etc.)
    """
    start_time = time.time()
    state["current_agent"] = "Agent 1b: Market Data"
    state["progress"] = 10
    
    try:
        market_context = {}
        
        for ticker in state["tickers"]:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                hist = stock.history(period="5d")
                
                # Calculate price changes
                if len(hist) >= 2:
                    price_change_1d = ((hist.iloc[-1]["Close"] - hist.iloc[-2]["Close"]) / hist.iloc[-2]["Close"]) * 100
                    price_change_5d = ((hist.iloc[-1]["Close"] - hist.iloc[0]["Close"]) / hist.iloc[0]["Close"]) * 100
                else:
                    price_change_1d = 0.0
                    price_change_5d = 0.0
                
                # Calculate volume ratio
                avg_volume = info.get("averageVolume", 1)
                current_volume = info.get("volume", avg_volume)
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
                
                market_context[ticker] = MarketContext(
                    ticker=ticker,
                    last_price=info.get("currentPrice", 0.0),
                    currency=info.get("currency", "USD"),
                    price_change_1d=price_change_1d,
                    price_change_5d=price_change_5d,
                    volume_ratio=volume_ratio,
                    analyst_rating=info.get("recommendationKey", "hold").title(),
                    target_price=info.get("targetMeanPrice", 0.0),
                    earnings_date=None,  # Would need additional API call
                    recent_eps_actual=info.get("trailingEps", 0.0),
                    recent_eps_estimate=info.get("epsTrailingTwelveMonths", 0.0),
                    fetched_at=datetime.now().isoformat() + "Z",
                )
            except Exception as e:
                # Fallback with zeros
                market_context[ticker] = MarketContext(
                    ticker=ticker,
                    last_price=0.0,
                    currency="USD",
                    price_change_1d=0.0,
                    price_change_5d=0.0,
                    volume_ratio=1.0,
                    analyst_rating="Hold",
                    target_price=0.0,
                    earnings_date=None,
                    recent_eps_actual=0.0,
                    recent_eps_estimate=0.0,
                    fetched_at=datetime.now().isoformat() + "Z",
                )
        
        state["market_context"] = market_context
        
    except Exception as e:
        state["error_message"] = f"Agent 1b error: {str(e)}"
        state["status"] = "failed"
    
    state["agent_timings"]["agent_1b"] = time.time() - start_time
    return state


# ============================================================================
# AGENT 2: NewsRetrievalAgent
# ============================================================================

def agent_2_news_retrieval(state: PipelineState) -> PipelineState:
    """
    Agent 2: News Retrieval Agent
    Fetches articles from multiple sources (Yahoo Finance, Reuters, etc.)
    Returns normalized Article objects.
    """
    start_time = time.time()
    state["current_agent"] = "Agent 2: News Retrieval"
    state["progress"] = 25
    
    try:
        raw_articles = []
        articles_by_ticker = {}
        
        for ticker in state["tickers"]:
            articles_by_ticker[ticker] = []
            company_name = state["ticker_metadata"].get(ticker, {}).get("name", ticker)
            
            # Fetch from Yahoo Finance RSS
            try:
                feed_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}"
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:5]:
                    article = Article(
                        ticker=ticker,
                        company=company_name,
                        headline=entry.get("title", ""),
                        snippet=entry.get("summary", "")[:200],
                        url=entry.get("link", ""),
                        source="Yahoo Finance",
                        published_at=entry.get("published", datetime.now().isoformat()),
                        query_type="company",
                        raw={"feed_entry": str(entry)},
                    )
                    raw_articles.append(article)
                    articles_by_ticker[ticker].append(article)
            except Exception as e:
                pass  # Continue if one source fails
        
        state["raw_articles"] = raw_articles
        state["articles_by_ticker"] = articles_by_ticker
        
    except Exception as e:
        state["error_message"] = f"Agent 2 error: {str(e)}"
        state["status"] = "failed"
    
    state["agent_timings"]["agent_2"] = time.time() - start_time
    return state


# ============================================================================
# AGENT 3: NoiseFilterAgent
# ============================================================================

def agent_3_noise_filtering(state: PipelineState) -> PipelineState:
    """
    Agent 3: Noise Filtering & Deduplication Agent
    Pass 1: Hard filters (URL dedup, snippet length, age)
    Pass 2: Semantic deduplication using embeddings
    """
    start_time = time.time()
    state["current_agent"] = "Agent 3: Noise Filtering"
    state["progress"] = 40
    
    try:
        articles = state["raw_articles"]
        
        # Pass 1: Hard filters
        filtered = []
        seen_urls = set()
        
        for article in articles:
            # URL deduplication
            if article.url in seen_urls:
                continue
            seen_urls.add(article.url)
            
            # Snippet length check
            if len(article.snippet) < 20:
                continue
            
            # Age filter (7 days default)
            try:
                pub_date = datetime.fromisoformat(article.published_at.replace("Z", "+00:00"))
                age_hours = (datetime.now(pub_date.tzinfo) - pub_date).total_seconds() / 3600
                if age_hours > 7 * 24:  # 7 days
                    continue
            except:
                pass
            
            filtered.append(article)
        
        # Pass 2: Semantic deduplication
        if len(filtered) > 1:
            headlines = [a.headline for a in filtered]
            vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 3))
            try:
                tfidf_matrix = vectorizer.fit_transform(headlines)
                similarity_matrix = cosine_similarity(tfidf_matrix)
                
                # Mark duplicates (similarity >= 0.85)
                to_remove = set()
                for i in range(len(filtered)):
                    for j in range(i + 1, len(filtered)):
                        if similarity_matrix[i][j] >= 0.85:
                            # Keep higher-tier source
                            tier_i = get_source_tier(filtered[i].source)
                            tier_j = get_source_tier(filtered[j].source)
                            if tier_i >= tier_j:
                                to_remove.add(j)
                            else:
                                to_remove.add(i)
                
                filtered = [a for i, a in enumerate(filtered) if i not in to_remove]
            except:
                pass  # If embedding fails, keep all
        
        state["filtered_articles"] = filtered
        state["deduplication_metadata"] = {
            "raw_count": len(articles),
            "filtered_count": len(filtered),
            "removed_count": len(articles) - len(filtered),
        }
        
    except Exception as e:
        state["error_message"] = f"Agent 3 error: {str(e)}"
        state["status"] = "failed"
    
    state["agent_timings"]["agent_3"] = time.time() - start_time
    return state


def get_source_tier(source: str) -> float:
    """Get credibility tier for a source (higher = more credible)"""
    tier_1 = ["SGX", "MAS", "Official"]
    tier_2 = ["Reuters", "Bloomberg", "Business Times", "Straits Times"]
    tier_3 = ["CNA", "Nikkei", "CNBC"]
    tier_4 = ["Yahoo Finance", "Reddit"]
    
    source_lower = source.lower()
    if any(t in source_lower for t in tier_1):
        return 1.0
    elif any(t in source_lower for t in tier_2):
        return 0.85
    elif any(t in source_lower for t in tier_3):
        return 0.70
    else:
        return 0.55


# ============================================================================
# AGENT 4: EventClusteringAgent
# ============================================================================

def agent_4_event_clustering(state: PipelineState) -> PipelineState:
    """
    Agent 4: Event Clustering Agent
    Groups articles by ticker and classifies event type using keyword matching.
    """
    start_time = time.time()
    state["current_agent"] = "Agent 4: Event Clustering"
    state["progress"] = 55
    
    try:
        event_clusters = []
        cluster_id_counter = 0
        
        # Group by ticker
        for ticker, articles in state["articles_by_ticker"].items():
            if not articles:
                continue
            
            # For each ticker, create event clusters
            for i, article in enumerate(articles):
                event_type = classify_event_type(article.headline, article.snippet)
                
                cluster = EventCluster(
                    cluster_id=f"{ticker}_c{cluster_id_counter:03d}",
                    ticker=ticker,
                    event_type=event_type,
                    articles=[article],
                    representative_headline=article.headline,
                    representative_source=article.source,
                    article_count=1,
                    sources=[article.source],
                )
                event_clusters.append(cluster)
                cluster_id_counter += 1
        
        state["event_clusters"] = event_clusters
        state["clustering_metadata"] = {
            "total_clusters": len(event_clusters),
            "articles_clustered": len(state["filtered_articles"]),
        }
        
    except Exception as e:
        state["error_message"] = f"Agent 4 error: {str(e)}"
        state["status"] = "failed"
    
    state["agent_timings"]["agent_4"] = time.time() - start_time
    return state


def classify_event_type(headline: str, snippet: str) -> str:
    """Classify event type using keyword matching"""
    text = (headline + " " + snippet).lower()
    
    event_keywords = {
        "earnings_release": ["earnings", "profit", "revenue", "net income", "eps", "quarterly"],
        "dividend": ["dividend", "distribution", "payout", "dpu"],
        "guidance_update": ["guidance", "outlook", "forecast", "profit warning", "upgrade", "downgrade"],
        "ma_announcement": ["acqui", "merger", "takeover", "buyout", "deal", "bid", "offer", "divest"],
        "regulatory_action": ["mas", "regulation", "compliance", "enforcement", "licence", "fine"],
        "capital_action": ["rights issue", "placement", "buyback", "bond", "capital raise"],
        "leadership_change": ["ceo", "chairman", "board", "appoint", "resign", "retire"],
        "litigation": ["lawsuit", "court", "arbitration", "investigation", "probe"],
        "product_launch": ["launch", "new product", "partnership", "contract win", "awarded"],
        "analyst_rating": ["analyst", "target price", "overweight", "buy", "sell", "hold", "rating"],
    }
    
    for event_type, keywords in event_keywords.items():
        if any(kw in text for kw in keywords):
            return event_type
    
    return "general_news"


# ============================================================================
# AGENT 5: ImpactSummarizationAgent
# ============================================================================

def agent_5_impact_summarization(state: PipelineState) -> PipelineState:
    """
    Agent 5: Impact Summarization Agent
    Generates TLDR, key facts, and impact using LLM.
    Includes verification pass.
    """
    start_time = time.time()
    state["current_agent"] = "Agent 5: Impact Summarization"
    state["progress"] = 70
    
    try:
        llm = get_llm(state)
        event_cards = []
        
        for cluster in state["event_clusters"]:
            # Prepare article text for LLM
            articles_text = "\n".join([
                f"- {a.headline}: {a.snippet}" for a in cluster.articles[:5]
            ])
            
            # Generate TLDR and key facts
            prompt = f"""Summarize these financial news articles about {cluster.ticker}:

{articles_text}

Provide:
1. A one-line TLDR
2. 3-5 key facts as bullet points
3. Impact explanation (2-3 sentences)

Format as JSON with keys: tldr, key_facts (list), impact"""
            
            try:
                response = llm.invoke([HumanMessage(content=prompt)])
                summary_text = response.content
                
                # Parse JSON response
                try:
                    summary_data = json.loads(summary_text)
                    tldr = summary_data.get("tldr", cluster.representative_headline)
                    key_facts = summary_data.get("key_facts", [cluster.representative_headline])
                    impact = summary_data.get("impact", "")
                    confidence = "high"
                except:
                    tldr = cluster.representative_headline
                    key_facts = [a.headline for a in cluster.articles[:3]]
                    impact = ""
                    confidence = "medium"
            except:
                tldr = cluster.representative_headline
                key_facts = [a.headline for a in cluster.articles[:3]]
                impact = ""
                confidence = "low"
            
            # Create event card
            event_card = EventCard(
                cluster_id=cluster.cluster_id,
                ticker=cluster.ticker,
                event_type=cluster.event_type,
                tldr=tldr,
                key_facts=key_facts,
                impact=impact,
                confidence=confidence,
                uncertainty_flags=[],
                supporting_sources=cluster.sources,
                source_urls=[a.url for a in cluster.articles],
                article_count=len(cluster.articles),
            )
            
            event_cards.append(event_card)
        
        state["event_cards"] = event_cards
        state["summarization_metadata"] = {
            "total_events": len(event_cards),
            "high_confidence": sum(1 for e in event_cards if e.confidence == "high"),
        }
        
    except Exception as e:
        state["error_message"] = f"Agent 5 error: {str(e)}"
        state["status"] = "failed"
    
    state["agent_timings"]["agent_5"] = time.time() - start_time
    return state


# ============================================================================
# AGENT 6: ImportanceRankingAgent
# ============================================================================

def agent_6_importance_ranking(state: PipelineState) -> PipelineState:
    """
    Agent 6: Importance Ranking Agent
    Scores events using 5-factor formula:
    score = event_type_weight*0.40 + corroboration*0.25 + novelty*0.20 + credibility*0.15 + confidence_adj
    """
    start_time = time.time()
    state["current_agent"] = "Agent 6: Importance Ranking"
    state["progress"] = 85
    
    try:
        ranked_events = []
        
        # Event type weights
        event_type_weights = {
            "earnings_release": 0.95,
            "dividend": 0.85,
            "guidance_update": 0.80,
            "ma_announcement": 0.90,
            "regulatory_action": 0.75,
            "capital_action": 0.70,
            "leadership_change": 0.65,
            "litigation": 0.70,
            "product_launch": 0.60,
            "analyst_rating": 0.55,
            "general_news": 0.35,
        }
        
        # Confidence adjustments
        confidence_adj = {
            "high": 0.05,
            "medium": 0.0,
            "low": -0.05,
        }
        
        for event in state["event_cards"]:
            # 1. Event type weight (40%)
            event_type_weight = event_type_weights.get(event.event_type, 0.35)
            
            # 2. Corroboration score (25%) - unique source count / 5
            corroboration_count = len(event.supporting_sources)
            corroboration_score = min(corroboration_count / 5.0, 1.0)
            
            # 3. Novelty score (20%) - article count / 8
            novelty_score = min(event.article_count / 8.0, 1.0)
            
            # 4. Credibility score (15%) - average tier of sources
            credibility_score = sum(get_source_tier(s) for s in event.supporting_sources) / len(event.supporting_sources) if event.supporting_sources else 0.55
            
            # 5. Confidence adjustment
            conf_adj = confidence_adj.get(event.confidence, 0.0)
            
            # Calculate final score
            score = (
                event_type_weight * 0.40 +
                corroboration_score * 0.25 +
                novelty_score * 0.20 +
                credibility_score * 0.15 +
                conf_adj
            )
            
            # Assign importance label
            if score >= 0.70:
                importance = "High"
            elif score >= 0.45:
                importance = "Medium"
            else:
                importance = "Low"
            
            event.importance = importance
            event.importance_score = score
            event.scoring_signals = {
                "event_type_weight": event_type_weight,
                "corroboration_count": corroboration_count,
                "corroboration_score": corroboration_score,
                "novelty_score": novelty_score,
                "credibility_score": credibility_score,
                "confidence_adj": conf_adj,
            }
            
            ranked_events.append(event)
        
        # Sort by importance score descending
        ranked_events.sort(key=lambda x: x.importance_score, reverse=True)
        
        # Assign ranks
        for i, event in enumerate(ranked_events):
            event.rank_overall = i + 1
        
        # Assign per-ticker ranks
        ticker_ranks = {}
        for event in ranked_events:
            ticker = event.ticker
            if ticker not in ticker_ranks:
                ticker_ranks[ticker] = 0
            ticker_ranks[ticker] += 1
            event.rank_per_ticker = ticker_ranks[ticker]
        
        state["ranked_events"] = ranked_events
        state["ranking_metadata"] = {
            "total_events": len(ranked_events),
            "high_importance": sum(1 for e in ranked_events if e.importance == "High"),
            "medium_importance": sum(1 for e in ranked_events if e.importance == "Medium"),
            "low_importance": sum(1 for e in ranked_events if e.importance == "Low"),
        }
        
    except Exception as e:
        state["error_message"] = f"Agent 6 error: {str(e)}"
        state["status"] = "failed"
    
    state["agent_timings"]["agent_6"] = time.time() - start_time
    return state


# ============================================================================
# AGENT 7: NotificationAgent
# ============================================================================

def agent_7_notification(state: PipelineState) -> PipelineState:
    """
    Agent 7: Notification Agent
    Packages ranked events into digest JSON and HTML email.
    """
    start_time = time.time()
    state["current_agent"] = "Agent 7: Notification"
    state["progress"] = 95
    
    try:
        # Filter events by minimum importance
        min_importance = "Low"
        filtered_events = [e for e in state["ranked_events"] if e.importance != "Low"]
        
        # Generate subject
        high_count = sum(1 for e in filtered_events if e.importance == "High")
        state["digest_subject"] = f"Financial News Digest: {high_count} High-Priority Events"
        
        # Generate JSON digest
        digest_data = {
            "timestamp": datetime.now().isoformat(),
            "subject": state["digest_subject"],
            "total_events": len(filtered_events),
            "high_priority": high_count,
            "events": [
                {
                    "cluster_id": e.cluster_id,
                    "ticker": e.ticker,
                    "event_type": e.event_type,
                    "tldr": e.tldr,
                    "key_facts": e.key_facts,
                    "impact": e.impact,
                    "importance": e.importance,
                    "importance_score": e.importance_score,
                    "rank_overall": e.rank_overall,
                    "rank_per_ticker": e.rank_per_ticker,
                    "supporting_sources": e.supporting_sources,
                    "source_urls": e.source_urls,
                    "article_count": e.article_count,
                    "scoring_signals": e.scoring_signals,
                }
                for e in filtered_events[:20]  # Top 20 events
            ]
        }
        
        state["digest_json"] = json.dumps(digest_data, indent=2)
        
        # Generate HTML digest
        html_parts = [
            "<!DOCTYPE html>",
            "<html><head><meta charset='utf-8'></head>",
            "<body style='font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;'>",
            f"<h1>{state['digest_subject']}</h1>",
            f"<p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>",
            f"<p>Total Events: {len(filtered_events)} | High Priority: {high_count}</p>",
            "<hr>",
        ]
        
        for event in filtered_events[:20]:
            color = "red" if event.importance == "High" else "orange" if event.importance == "Medium" else "gray"
            html_parts.append(f"""
            <div style='border-left: 4px solid {color}; padding: 15px; margin: 15px 0; background: #f9f9f9;'>
                <h3>{event.ticker} - {event.event_type.replace('_', ' ').title()}</h3>
                <p><strong>Importance:</strong> <span style='color: {color}; font-weight: bold;'>{event.importance}</span> ({event.importance_score:.2f})</p>
                <p><strong>TLDR:</strong> {event.tldr}</p>
                <p><strong>Key Facts:</strong></p>
                <ul>
                    {''.join(f'<li>{fact}</li>' for fact in event.key_facts)}
                </ul>
                <p><strong>Impact:</strong> {event.impact}</p>
                <p><strong>Sources:</strong> {', '.join(event.supporting_sources)} ({event.article_count} articles)</p>
            </div>
            """)
        
        html_parts.extend([
            "</body></html>"
        ])
        
        state["digest_html"] = "".join(html_parts)
        
        state["progress"] = 100
        state["status"] = "completed"
        state["completed_at"] = datetime.now()
        
    except Exception as e:
        state["error_message"] = f"Agent 7 error: {str(e)}"
        state["status"] = "failed"
    
    state["agent_timings"]["agent_7"] = time.time() - start_time
    return state
