import streamlit as st

def init_session():
    if "watchlist" not in st.session_state:
        st.session_state.watchlist = dict()

    if "settings" not in st.session_state:
        st.session_state.settings = []

    if "dashboard" not in st.session_state:
        st.session_state.dashboard = []

    if "running" not in st.session_state:
        st.session_state.running = False

    if "pipeline_result" not in st.session_state:
        st.session_state.pipeline_result = None

    if "step_logs" not in st.session_state:
        st.session_state.step_logs = []

    if "current_step" not in st.session_state:
        st.session_state.current_step = 0

      # Digest history
    if "digest_history" not in st.session_state:
        st.session_state.digest_history = []
    
    if "selected_digest" not in st.session_state:
        st.session_state.selected_digest = None

def update_watchlist(tickers):
    """Update watchlist in session state"""
    st.session_state.watchlist = tickers

def reset_digest_state():
    """Reset digest generation state"""
    st.session_state.generating_digest = False
    st.session_state.digest_progress = 0
    st.session_state.current_agent = ""
    st.session_state.current_digest = None

def set_current_digest(digest):
    """Set current digest in session state"""
    st.session_state.current_digest = digest

def add_to_history(digest):
    """Add digest to history"""
    if st.session_state.digest_history is None:
        st.session_state.digest_history = []
    st.session_state.digest_history.insert(0, digest)
