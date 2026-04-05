"""
Watchlist management page
"""

import streamlit as st
import pandas as pd
from utils.database import (
    get_user_watchlist, add_ticker, remove_ticker
)
from utils.session import update_watchlist

def show():
    """Display watchlist page"""
    st.title("📊 Stock Watchlist")
    st.markdown("Manage your stock tickers for news monitoring")
    
    user_id = st.session_state.user_id
    
    # Add new ticker section
    st.subheader("Add New Ticker")
    col1, col2 = st.columns([3, 1])
    
    with col1:
        new_ticker = st.text_input(
            "Enter stock ticker symbol",
            placeholder="e.g., AAPL, NVDA, TSLA",
            label_visibility="collapsed"
        ).upper()
    
    with col2:
        if st.button("➕ Add", use_container_width=True):
            if new_ticker:
                if add_ticker(user_id, new_ticker):
                    st.success(f"✓ Added {new_ticker} to watchlist")
                    st.rerun()
                else:
                    st.error(f"✗ {new_ticker} already in watchlist or invalid")
            else:
                st.warning("Please enter a ticker symbol")
    
    st.markdown("---")
    
    # Display current watchlist
    st.subheader("Your Watchlist")
    
    watchlist = get_user_watchlist(user_id)
    
    if watchlist:
        # Create DataFrame for display
        df = pd.DataFrame({
            "Ticker": watchlist,
            "Status": ["✓ Active"] * len(watchlist)
        })
        
        # Display as table
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown("---")
        
        # Remove ticker section
        st.subheader("Remove Ticker")
        ticker_to_remove = st.selectbox(
            "Select ticker to remove",
            watchlist,
            label_visibility="collapsed"
        )
        
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🗑️ Remove", use_container_width=True):
                if remove_ticker(user_id, ticker_to_remove):
                    st.success(f"✓ Removed {ticker_to_remove} from watchlist")
                    st.rerun()
                else:
                    st.error("Failed to remove ticker")
        
        st.markdown("---")
        
        # Statistics
        st.subheader("Watchlist Statistics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Tickers", len(watchlist))
        
        with col2:
            st.metric("Active Monitoring", "✓ Yes")
        
        with col3:
            st.metric("Update Frequency", "On Demand")
        
        st.info(
            f"📌 You are monitoring {len(watchlist)} stock ticker(s). "
            f"Go to Dashboard to generate a news digest."
        )
    
    else:
        st.warning("Your watchlist is empty. Add some tickers to get started!")
        
        # Suggestions
        st.subheader("Popular Tickers")
        col1, col2, col3, col4 = st.columns(4)
        
        suggestions = ["AAPL", "NVDA", "TSLA", "MSFT"]
        
        with col1:
            if st.button("Add AAPL"):
                add_ticker(user_id, "AAPL")
                st.rerun()
        
        with col2:
            if st.button("Add NVDA"):
                add_ticker(user_id, "NVDA")
                st.rerun()
        
        with col3:
            if st.button("Add TSLA"):
                add_ticker(user_id, "TSLA")
                st.rerun()
        
        with col4:
            if st.button("Add MSFT"):
                add_ticker(user_id, "MSFT")
                st.rerun()
