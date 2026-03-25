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



def update_watchlist(tickers):
    """Update watchlist in session state"""
    st.session_state.watchlist = tickers