"""
Digest generation and display page
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from utils.database import (
    get_user_watchlist, save_digest, get_llm_config
)
from utils.pipeline import (
    execute_pipeline, format_event_for_display, 
    get_importance_emoji, get_importance_color
)
from utils.session import add_to_history

def show():
    """Display digest generation page"""
    st.title("📰 Financial News Digest")
    st.markdown("Generate AI-powered news digests for your stock watchlist")
    
    user_id = st.session_state.user_id
    watchlist = get_user_watchlist(user_id)
    
    if not watchlist:
        st.warning(
            "⚠️ Your watchlist is empty. "
            "[Add tickers in the Watchlist section](/?page=watchlist) to generate digests."
        )
        return
    
    # Digest generation section
    st.subheader("Generate New Digest")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"**Monitoring {len(watchlist)} ticker(s):** {', '.join(watchlist)}")
    
    with col2:
        generate_button = st.button(
            "⚡ Generate Digest",
            use_container_width=True,
            type="primary"
        )
    
    if generate_button:
        # Get LLM config
        llm_config = get_llm_config(user_id)
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        agent_info = st.empty()
        
        try:
            status_text.info("🔄 Starting pipeline execution...")
            
            # Execute pipeline
            result = execute_pipeline(
                tickers=watchlist,
                user_id=user_id,
                llm_provider=llm_config.get("provider", "openai"),
                llm_api_key=llm_config.get("api_key", "")
            )
            
            if result["status"] == "completed":
                progress_bar.progress(100)
                status_text.success("✓ Digest generated successfully!")
                
                # Save to database
                digest_id = save_digest(user_id, result)
                add_to_history(result)
                
                st.session_state.current_digest = result
                
                # Display results
                st.markdown("---")
                display_digest_results(result)
            
            else:
                status_text.error(f"✗ Pipeline failed: {result.get('error', 'Unknown error')}")
        
        except Exception as e:
            status_text.error(f"✗ Error: {str(e)}")
    
    # Display current digest if available
    if st.session_state.current_digest:
        st.markdown("---")
        st.subheader("Latest Digest")
        display_digest_results(st.session_state.current_digest)

def display_digest_results(digest: dict):
    """Display digest results"""
    
    if not digest or digest.get("status") != "completed":
        return
    
    # Summary metrics
    st.subheader("📊 Digest Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Events", digest["event_counts"]["total"])
    
    with col2:
        st.metric("🔴 High Priority", digest["event_counts"]["high"])
    
    with col3:
        st.metric("🟠 Medium Priority", digest["event_counts"]["medium"])
    
    with col4:
        st.metric("🟢 Low Priority", digest["event_counts"]["low"])
    
    st.markdown("---")
    
    # Filter events by importance
    st.subheader("📰 Events")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        importance_filter = st.multiselect(
            "Filter by importance",
            ["HIGH", "MEDIUM", "LOW"],
            default=["HIGH", "MEDIUM", "LOW"],
            label_visibility="collapsed"
        )
    
    # Display events
    events = digest.get("events", [])
    filtered_events = [
        e for e in events 
        if e["importance"].upper() in importance_filter
    ]
    
    if not filtered_events:
        st.info("No events match the selected filters")
    else:
        for idx, event in enumerate(filtered_events):
            display_event_card(event, idx)
    
    st.markdown("---")
    
    # Export options
    st.subheader("📥 Export Digest")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📄 Download as HTML"):
            html_content = digest.get("html_digest", "")
            st.download_button(
                label="Download HTML",
                data=html_content,
                file_name="digest.html",
                mime="text/html"
            )
    
    with col2:
        if st.button("📝 Download as Text"):
            text_content = digest.get("plain_text_digest", "")
            st.download_button(
                label="Download Text",
                data=text_content,
                file_name="digest.txt",
                mime="text/plain"
            )

def display_event_card(event: dict, idx: int):
    """Display individual event card"""
    
    importance = event["importance"].upper()
    emoji = get_importance_emoji(importance)
    color = get_importance_color(importance)
    
    # Create card container
    with st.container(border=True):
        # Header
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.markdown(f"**{event['ticker']}** • {event['event_type']}")
        
        with col2:
            st.markdown(f"{emoji} {importance}")
        
        with col3:
            st.markdown(f"Score: {event['score']}/100")
        
        # Headline
        st.markdown(f"### {event['headline']}")
        
        # TLDR
        st.markdown(f"**TLDR:** {event['tldr']}")
        
        # Key bullets
        if event.get("key_bullets"):
            st.markdown("**Key Points:**")
            for bullet in event["key_bullets"]:
                st.markdown(f"• {bullet}")
        
        # Impact
        if event.get("impact"):
            st.markdown(f"**Impact:** {event['impact']}")
        
        # Metadata
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.caption(f"📊 Sources: {event['source_count']}")
        
        with col2:
            st.caption(f"✓ Verification: {event['verification_status']}")
        
        with col3:
            st.caption(f"🔗 Sources available")
