"""
Session state management for Streamlit
"""

import streamlit as st
from datetime import datetime

def init_session_state():
    """Initialize Streamlit session state variables"""
    
    # User session
    if "user_id" not in st.session_state:
        st.session_state.user_id = 1  # Default user (in production, use auth)
    
    if "user_name" not in st.session_state:
        st.session_state.user_name = "User"
    
    # Watchlist
    if "watchlist" not in st.session_state:
        st.session_state.watchlist = []
    
    if "new_ticker" not in st.session_state:
        st.session_state.new_ticker = ""
    
    # Digest generation
    if "generating_digest" not in st.session_state:
        st.session_state.generating_digest = False
    
    if "current_digest" not in st.session_state:
        st.session_state.current_digest = None
    
    if "digest_progress" not in st.session_state:
        st.session_state.digest_progress = 0
    
    if "current_agent" not in st.session_state:
        st.session_state.current_agent = ""
    
    # Settings
    if "llm_provider" not in st.session_state:
        st.session_state.llm_provider = "openai"
    
    if "llm_api_key" not in st.session_state:
        st.session_state.llm_api_key = ""
    
    # Digest history
    if "digest_history" not in st.session_state:
        st.session_state.digest_history = []
    
    if "selected_digest" not in st.session_state:
        st.session_state.selected_digest = None
    
    # UI state
    if "show_event_details" not in st.session_state:
        st.session_state.show_event_details = None
    
    if "filter_importance" not in st.session_state:
        st.session_state.filter_importance = ["High", "Medium", "Low"]

def reset_digest_state():
    """Reset digest generation state"""
    st.session_state.generating_digest = False
    st.session_state.digest_progress = 0
    st.session_state.current_agent = ""
    st.session_state.current_digest = None

def update_watchlist(tickers):
    """Update watchlist in session state"""
    st.session_state.watchlist = tickers

def set_current_digest(digest):
    """Set current digest in session state"""
    st.session_state.current_digest = digest

def add_to_history(digest):
    """Add digest to history"""
    if st.session_state.digest_history is None:
        st.session_state.digest_history = []
    st.session_state.digest_history.insert(0, digest)
