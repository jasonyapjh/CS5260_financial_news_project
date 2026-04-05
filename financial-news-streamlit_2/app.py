"""
Financial News Intelligence - Streamlit Application
A multi-agent AI system for personalized financial news digests
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv

# Import custom modules
from pages import watchlist, digest, history, settings
from utils.database import init_db, get_user_watchlist
from utils.session import init_session_state

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Financial News Intelligence",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
init_session_state()

# Initialize database
init_db()

# Custom CSS for better styling
st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    .stTabs [data-baseweb="tab-list"] button {
        font-size: 1.1rem;
        padding: 0.5rem 1.5rem;
    }
    .event-card {
        border-left: 4px solid #1f77b4;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.25rem;
    }
    .high-importance {
        border-left-color: #d62728;
    }
    .medium-importance {
        border-left-color: #ff7f0e;
    }
    .low-importance {
        border-left-color: #2ca02c;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar navigation
with st.sidebar:
    st.title("📰 Financial News Intelligence")
    st.markdown("---")
    
    # Navigation menu
    page = st.radio(
        "Navigation",
        ["Dashboard", "Watchlist", "Digest History", "Settings"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # User info
    if "user_id" in st.session_state:
        st.markdown(f"**User ID:** {st.session_state.user_id}")
    
    st.markdown("---")
    st.markdown("""
    **About this app:**
    
    This application uses a 7-agent AI pipeline to:
    1. Retrieve news for your stock tickers
    2. Cluster and summarize events
    3. Rank by importance
    4. Generate curated digests
    
    **Supported LLM Providers:**
    - OpenAI (GPT-4, GPT-3.5)
    - Google Gemini
    """)

# Main content area
if page == "Dashboard":
    digest.show()
elif page == "Watchlist":
    watchlist.show()
elif page == "Digest History":
    history.show()
elif page == "Settings":
    settings.show()

# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #888; font-size: 0.9rem;">
    Financial News Intelligence v1.0 | Powered by LangGraph & Streamlit
    </div>
    """,
    unsafe_allow_html=True
)
