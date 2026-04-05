"""
Digest history and archive page
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from utils.database import (
    get_digest_history, get_digest_detail, delete_digest
)
from pages.digest import display_event_card

def show():
    """Display digest history page"""
    st.title("📚 Digest History")
    st.markdown("View and manage your previous news digests")
    
    user_id = st.session_state.user_id
    
    # Get history
    history = get_digest_history(user_id)
    
    if not history:
        st.info("No digests generated yet. Go to Dashboard to create one!")
        return
    
    st.subheader("Your Digests")
    
    # Create DataFrame for display
    df_data = []
    for digest in history:
        df_data.append({
            "Date": digest["created_at"],
            "Subject": digest["subject"],
            "Tickers": ", ".join(digest["tickers"]),
            "Events": digest["event_counts"].get("total", 0),
            "ID": digest["id"]
        })
    
    df = pd.DataFrame(df_data)
    
    # Display as interactive table
    st.dataframe(
        df[["Date", "Subject", "Tickers", "Events"]],
        use_container_width=True,
        hide_index=True
    )
    
    st.markdown("---")
    
    # Select digest to view
    st.subheader("View Digest Details")
    
    selected_subject = st.selectbox(
        "Select a digest to view",
        [d["subject"] for d in history],
        label_visibility="collapsed"
    )
    
    # Find selected digest
    selected_digest_data = next(
        (d for d in history if d["subject"] == selected_subject),
        None
    )
    
    if selected_digest_data:
        # Get full digest details
        digest = get_digest_detail(selected_digest_data["id"])
        
        if digest:
            # Display digest info
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Created", digest["created_at"][:10])
            
            with col2:
                st.metric("Total Events", digest["event_counts"]["total"])
            
            with col3:
                st.metric("Tickers", len(digest["tickers"]))
            
            st.markdown("---")
            
            # Display events
            st.subheader("Events")
            
            col1, col2 = st.columns([3, 1])
            with col2:
                importance_filter = st.multiselect(
                    "Filter by importance",
                    ["HIGH", "MEDIUM", "LOW"],
                    default=["HIGH", "MEDIUM", "LOW"],
                    label_visibility="collapsed"
                )
            
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
            st.subheader("Export")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📄 Download HTML"):
                    st.download_button(
                        label="HTML",
                        data=digest.get("html_body", ""),
                        file_name=f"digest_{digest['id']}.html",
                        mime="text/html"
                    )
            
            with col2:
                if st.button("📝 Download Text"):
                    st.download_button(
                        label="Text",
                        data=digest.get("plain_text_body", ""),
                        file_name=f"digest_{digest['id']}.txt",
                        mime="text/plain"
                    )
            
            with col3:
                if st.button("🗑️ Delete Digest"):
                    if delete_digest(digest["id"]):
                        st.success("Digest deleted")
                        st.rerun()
                    else:
                        st.error("Failed to delete digest")
