import streamlit as st
import pandas as pd
from datetime import datetime
from utils.database import (
    get_digest_history, get_digest_detail, delete_digest
)

# Constants aligned with your Dashboard
PRIORITY_COLORS = {"High": "#ef4444", "Medium": "#f97316", "Low": "#22c55e"}
PRIORITY_BG     = {"High": "#2a0a0a", "Medium": "#2a1400", "Low": "#0a2014"}
SENTIMENT_EMOJI = {"bullish": "▲", "bearish": "▼", "neutral": "◆"}
SENTIMENT_COLOR = {"bullish": "#22c55e", "bearish": "#ef4444", "neutral": "#fbbf24"}

def display_event_card(event: dict, idx: int):
    """Display individual event card using the actual agent output schema"""
    
    label = event.get("importance", "Low")
    sent  = event.get("sentiment", "neutral")
    etype = event.get("event_type", "other")
    score = event.get("importance_score", 0)
    
    pcolor = PRIORITY_COLORS.get(label, "#22c55e")
    pbg    = PRIORITY_BG.get(label, "#0a2014")
    scolor = SENTIMENT_COLOR.get(sent, "#fbbf24")
    semoji = SENTIMENT_EMOJI.get(sent, "◆")
    
    with st.container(border=True):
        # Header Row
        col_title, col_score = st.columns([4, 1])
        
        with col_title:
            st.markdown(
                f"**{event.get('ticker', '???')}** &nbsp;·&nbsp; `{etype.replace('_',' ').title()}` "
                f"&nbsp; <span style='color:{pcolor}; background:{pbg}; padding:2px 6px; border-radius:4px; border:1px solid {pcolor}55;'>{label}</span>"
                f"&nbsp; <span style='color:{scolor};'>{semoji} {sent}</span>",
                unsafe_allow_html=True
            )
        
        with col_score:
            st.markdown(f"<div style='text-align:right; font-family:monospace; font-size:18px; font-weight:bold; color:{pcolor}'>{score}</div>", unsafe_allow_html=True)

        # Content
        st.markdown(f"### {event.get('representative_headline', 'No Headline')}")
        st.markdown(f"**TLDR:** {event.get('tldr', 'No summary available.')}")
        
        # Key Facts (mapped from key_facts in your agent output)
        facts = event.get("key_facts", [])
        if facts:
            for fact in facts:
                st.markdown(f"• {fact}")
        
        # Investment Impact
        impact = event.get("impact", "")
        if impact:
            st.info(f"**Impact:** {impact}")
        
        # Footer Metadata
        c1, c2, c3 = st.columns(3)
        c1.caption(f"📊 Sources: {event.get('article_count', 1)}")
        c2.caption(f"✓ Confidence: {event.get('confidence', 'medium')}")
        
        urls = event.get("source_urls", [])
        if urls:
            c3.caption(f"🔗 [Primary Source]({urls[0]})")

def show():
    st.title("📚 Digest History")
    st.caption("View and manage your previous news digests")
    
    # Get history from DB
    history = get_digest_history(0)
    
    if not history:
        st.info("No digests generated yet. Go to Dashboard to create one!")
        return
    
    # --- 1. History Overview Table ---
    df_data = []
    for digest in history:
        # Format the date for readability
        try:
            dt = datetime.fromisoformat(digest["created_at"].replace("Z", "+00:00"))
            date_str = dt.strftime("%Y-%m-%d %H:%M")
        except:
            date_str = digest["created_at"]

        df_data.append({
            "Date": date_str,
            "ID": digest["id"],
            "Tickers": ", ".join(digest.get("tickers", [])),
            "Events": digest.get("event_counts", {}).get("total", 0),
            "High": digest.get("event_counts", {}).get("high", 0),
        })
    
    df = pd.DataFrame(df_data).sort_values("Date", ascending=False)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    st.divider()
    
    # --- 2. Detail Viewer ---
    st.subheader("🔍 Detailed View")
    
    # Create a clean label for the selectbox
    digest_options = {f"{d['Date']} | ID: {d['ID']} ({d['Tickers']})": d['ID'] for d in df_data}
    selected_label = st.selectbox("Select a digest to explore", options=list(digest_options.keys()))
    selected_id = digest_options[selected_label]
    
    if selected_id:
        digest = get_digest_detail(selected_id)
        
        if digest:
            # Metrics Row
            m1, m2, m3 = st.columns(3)
            counts = digest.get("event_counts", {})
            m1.metric("High Priority", counts.get("high", 0))
            m2.metric("Total Events", counts.get("total", 0))
            m3.metric("Tickers", len(digest.get("tickers", [])))
            
            # Filters
            importance_filter = st.multiselect(
                "Filter by Importance",
                ["High", "Medium", "Low"],
                default=["High", "Medium", "Low"]
            )
            
            # Display the Events
            events = digest.get("events", [])
            filtered_events = [e for e in events if e.get("importance", "Low") in importance_filter]
            
            for idx, event in enumerate(filtered_events):
                display_event_card(event, idx)
            
            # --- 3. Management Actions ---
            st.divider()
            with st.expander("🛠️ Digest Management"):
                col1, col2, col3 = st.columns(3)
                
                # HTML Export
                html_data = digest.get("html_digest", "")
                col1.download_button(
                    "📄 Download HTML",
                    data=html_data,
                    file_name=f"fintel_digest_{selected_id}.html",
                    mime="text/html",
                    use_container_width=True
                )
                
                # Text Export
                text_data = digest.get("plain_text_digest", "")
                col2.download_button(
                    "📝 Download Text",
                    data=text_data,
                    file_name=f"fintel_digest_{selected_id}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
                
                # Delete
                if col3.button("🗑️ Delete Permanently", type="secondary", use_container_width=True):
                    if delete_digest(selected_id):
                        st.success("Deleted!")
                        st.rerun()