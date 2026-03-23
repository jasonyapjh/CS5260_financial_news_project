"""
Watchlist page for the Financial News App. 
"""

import streamlit as st
from streamlit_searchbox import st_searchbox
import yfinance as yf

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
    st.title("📈 My Watchlist")
    st.markdown("""
    Manage your stock watchlist to stay updated on the latest news and performance of your favorite companies.
    """)

    st.title("Stock Ticker Lookup")
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
            st.session_state.watchlist.append(selected_ticker)
            st.session_state.search_key_counter += 1
            st.rerun()  # Refresh to show the updated watchlist
    
    selected_to_remove = st.pills(
        label="Watchlist",
        options=st.session_state.watchlist,
        selection_mode="single",
        label_visibility="collapsed"
    )
    if selected_to_remove:
        st.session_state.watchlist.remove(selected_to_remove)
        st.rerun()



    #st.write("Current Watchlist:", st.session_state.watchlist)
