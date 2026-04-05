"""
Settings and configuration page
"""

import streamlit as st
from utils.database import get_llm_config, save_llm_config

def show():
    """Display settings page"""
    st.title("⚙️ Settings")
    st.markdown("Configure your application preferences")
    
    user_id = st.session_state.user_id
    
    # LLM Provider Configuration
    st.subheader("🤖 LLM Provider Configuration")
    
    st.markdown("""
    The application uses Large Language Models (LLMs) for:
    - Summarizing news articles
    - Clustering related events
    - Ranking event importance
    - Generating impact analysis
    """)
    
    # Get current config
    current_config = get_llm_config(user_id)
    
    # Provider selection
    provider = st.radio(
        "Select LLM Provider",
        ["OpenAI", "Google Gemini"],
        index=0 if current_config.get("provider", "openai") == "openai" else 1
    )
    
    provider_key = provider.lower().replace(" ", "")
    if provider == "Google Gemini":
        provider_key = "gemini"
    
    # API Key input
    st.markdown(f"### {provider} API Key")
    
    if provider == "OpenAI":
        st.markdown("""
        Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys)
        
        **Recommended Models:**
        - GPT-4 (most capable)
        - GPT-3.5 Turbo (faster, cost-effective)
        """)
    else:
        st.markdown("""
        Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
        
        **Recommended Models:**
        - Gemini Pro (most capable)
        - Gemini Pro Vision (multimodal)
        """)
    
    api_key = st.text_input(
        f"{provider} API Key",
        value=current_config.get("api_key", ""),
        type="password",
        placeholder="sk-... or AIza...",
        label_visibility="collapsed"
    )
    
    # Save configuration
    col1, col2 = st.columns([1, 3])
    
    with col1:
        if st.button("💾 Save Configuration", use_container_width=True):
            if api_key:
                save_llm_config(user_id, provider_key, api_key)
                st.success(f"✓ Configuration saved! Using {provider}")
                st.session_state.llm_provider = provider_key
                st.session_state.llm_api_key = api_key
            else:
                st.error("Please enter an API key")
    
    st.markdown("---")
    
    # Application Settings
    st.subheader("⚙️ Application Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Watchlist Settings**")
        max_tickers = st.slider(
            "Maximum tickers per watchlist",
            min_value=1,
            max_value=50,
            value=10,
            label_visibility="collapsed"
        )
        st.caption(f"Current limit: {max_tickers} tickers")
    
    with col2:
        st.markdown("**Digest Settings**")
        auto_export = st.checkbox(
            "Auto-export digests",
            value=False,
            label_visibility="collapsed"
        )
        st.caption("Automatically save digests to file")
    
    st.markdown("---")
    
    # About section
    st.subheader("ℹ️ About")
    
    st.markdown("""
    **Financial News Intelligence v1.0**
    
    A multi-agent AI system for personalized financial news digests.
    
    **Features:**
    - 7-agent LangGraph pipeline
    - Real-time news retrieval
    - Intelligent event clustering
    - Importance ranking
    - HTML & text export
    
    **Technology Stack:**
    - Streamlit (UI)
    - LangGraph (Agent orchestration)
    - OpenAI / Google Gemini (LLMs)
    - SQLite (Database)
    
    **Support:**
    For issues or feature requests, please contact support.
    """)
    
    st.markdown("---")
    
    # Advanced Settings
    with st.expander("🔧 Advanced Settings"):
        st.markdown("**Debug Information**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("User ID", user_id)
        
        with col2:
            st.metric("LLM Provider", current_config.get("provider", "openai").upper())
        
        with col3:
            st.metric("API Key Status", "✓ Configured" if current_config.get("api_key") else "✗ Not set")
        
        st.markdown("**Session Information**")
        st.json({
            "user_id": user_id,
            "llm_provider": st.session_state.get("llm_provider", "openai"),
            "watchlist_count": len(st.session_state.get("watchlist", [])),
            "digest_history_count": len(st.session_state.get("digest_history", [])),
        })
