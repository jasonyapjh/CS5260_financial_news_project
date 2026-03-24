import streamlit as st

def init_session():
    if "watchlist" not in st.session_state:
        st.session_state.watchlist = dict()

    if "settings" not in st.session_state:
        st.session_state.settings = []

    if "dashboard" not in st.session_state:
        st.session_state.dashboard = []

def update_watchlist(tickers):
    """Update watchlist in session state"""
    st.session_state.watchlist = tickers