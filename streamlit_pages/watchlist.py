"""
Watchlist page for the Financial News App. 
"""

import streamlit as st
from streamlit_searchbox import st_searchbox
import yfinance as yf
from utils.database import (
    get_user_watchlist, add_ticker, remove_ticker
)
def search_symbols(search_term: str):
    """
    Search Yahoo Finance for tickers based on company name.
    Returns a list of tuples: (label_to_show, value_to_return)
    """
    if not search_term or len(search_term) < 2:
        return []

    try:
        # yf.Search performs a real-time lookup
        search = yf.Search(search_term, max_results=8)
        
        # We want to show "Apple Inc. (AAPL)" but return just "AAPL"
        results = [
            (f"{q['longname']} ({q['symbol']})", q['symbol']) 
            for q in search.quotes 
            if 'longname' in q and 'symbol' in q
        ]
        return results
    except Exception:
        return []

if "search_key_counter" not in st.session_state:
    st.session_state.search_key_counter = 0

def show():
    st.markdown("""
        <style>
        /* 1. Target the button itself for padding and border */
        [data-testid="stBaseButton-pills"] {
            padding: 10px 20px !important;
            min-height: 50px !important;
            min-width: 200px !important;
            border: 1px solid #00d4ff !important; /* Optional: Cyan border to match your image */
            border-radius: 12px !important;
            margin: 5px !important; /* Add some spacing between pills */
                
        }

        /* 2. Target the Markdown container and paragraph inside the pill */
        [data-testid="stBaseButton-pills"] [data-testid="stMarkdownContainer"] p {
            font-size: 22px !important; /* Increase this number to make it even bigger */
            font-weight: 700 !important; /* Bold text */
            line-height: 1.2 !important;
            color: #00d4ff !important; /* Optional: Matches the text color to the border */
        }
        
        /* 3. Ensure the hover state looks good */
        [data-testid="stBaseButton-pills"]:hover {
            background-color: rgba(0, 212, 255, 0.1) !important;
            border-color: #ffffff !important;
        }
                
        [data-testid="stBaseButton-pills"] [data-testid="stMarkdownContainer"] p::after {
        content: " ✕"; /* This adds the icon visually */
        font-size: 25px !important;
        margin-left: 25px;
        opacity: 0.7;
        transition: opacity 0.2s;
        }

        [data-testid="stBaseButton-pills"]:hover [data-testid="stMarkdownContainer"] p::after {
        opacity: 1;
        color: #ff4b4b; /* Turns red on hover to signal deletion */
        }
        </style>
        """, unsafe_allow_html=True)
    st.markdown("""
        <style>
        /* 1. Target the button itself for padding and border */
        [data-testid="stBaseButton-pillsActive"] {
            padding: 10px 20px !important;
            min-height: 50px !important;
            border: 1px solid #00d4ff !important; /* Optional: Cyan border to match your image */
            border-radius: 12px !important;
            min-width: 200px !important;
            margin: 5px !important; /* Add some spacing between pills */
        }

        /* 2. Target the Markdown container and paragraph inside the pill */
        [data-testid="stBaseButton-pillsActive"] [data-testid="stMarkdownContainer"] p {
            font-size: 22px !important; /* Increase this number to make it even bigger */
            font-weight: 700 !important; /* Bold text */
            line-height: 1.2 !important;
            color: #00d4ff !important; /* Optional: Matches the text color to the border */
        }
        
        /* 3. Ensure the hover state looks good */
        [data-testid="stBaseButton-pillsActive"]:hover {
            background-color: rgba(0, 212, 255, 0.1) !important;
            border-color: #ffffff !important;
        }
                
        [data-testid="stBaseButton-pillsActive"] [data-testid="stMarkdownContainer"] p::after {
        content: " ✕"; /* This adds the icon visually */
        font-size: 25px !important;
        margin-left: 25px;
        opacity: 0.7;
        transition: opacity 0.2s;
        }

        [data-testid="stBaseButton-pillsActive"]:hover [data-testid="stMarkdownContainer"] p::after {
        opacity: 1;
        color: #ff4b4b; /* Turns red on hover to signal deletion */
        }
        </style>
        """, unsafe_allow_html=True)
    st.markdown("# 📈 My Watchlist")
    st.markdown("""
    Manage your stock watchlist to stay updated on the latest news and performance of your favorite companies.
    """)

    st.markdown("## Stock Ticker Lookup")
    search_key = f"stock_search_{st.session_state.search_key_counter}"

    # Create the searchbox
    selected_ticker = st_searchbox(
        search_symbols,
        placeholder="Type a company name (e.g. Apple)...",
        key=search_key,
        default='',
        clear_on_submit=True
    )

    if selected_ticker:
        if selected_ticker not in st.session_state.watchlist:
            add_ticker(0,  selected_ticker)
            st.session_state.search_key_counter += 1
            st.rerun()  # Refresh to show the updated watchlist
    
    watchlist = get_user_watchlist(0)
    
    if watchlist:
        for ticker, info in watchlist.items():
            st.session_state.watchlist[ticker] = {"active" : True if info.get('active') else False}
        st.markdown("---")

        with st.container(border=True):
            st.subheader("Current Watchlist")
            if st.session_state.watchlist:
                selected_to_remove = st.pills(
                    label="Watchlist",
                    options=st.session_state.watchlist,
                    selection_mode="single",
                    label_visibility="collapsed")
                if selected_to_remove:
                    st.session_state.watchlist.pop(selected_to_remove, None)
                    remove_ticker(0, selected_to_remove)
                    st.rerun() 

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
        st.info("Your watchlist is currently empty. Use the search box above to add stocks.")

    with st.container(border=True):
        st.subheader("Tips")
        st.markdown("""
        Add up to 8 stock tickers to your watchlist. Once added, you can generate a personalized news digest that analyzes important events for these companies.
        """)

  
    
    # # Display current watchlist
    # st.subheader("Your Watchlist")
    # # st.write("Current Watchlist:", st.session_state.watchlist)
