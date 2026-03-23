import streamlit as st

def init_session():
    if "watchlist" not in st.session_state:
        st.session_state.watchlist = []

    if "settings" not in st.session_state:
        st.session_state.settings = []

    