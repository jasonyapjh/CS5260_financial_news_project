"""
Watchlist page for the Financial News App. 
"""

import streamlit as st
from streamlit_searchbox import st_searchbox
import yfinance as yf

st.markdown("""
    <style>
    /* Increase font size and padding for the pills */
    button[data-baseweb="tab"] div, 
    .st-emotion-cache-12w0qpk p {
        font-size: 20px !important;
        font-weight: 600 !important;
    }
    
    /* Increase the actual "capsule" size */
    [data-testid="stPills"] div[role="listitem"] button {
        padding: 10px 20px !important;
        border-radius: 10px !important;
        border: 1px solid #00d4ff !important; /* Matches your cyan theme */
    }
    </style>
    """, unsafe_allow_html=True)
    
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
    
def onMultiselectChange():
    #st.session_state.watchlist = updated_watchlist
    print("Updated Watchlist:", st.session_state.watchlist)
    st.rerun()
    #st.button("Refresh Watchlist", on_click=st.rerun)

def show():
    st.title("📈 Watchlist")
    st.markdown("""
    This is where you can manage your stock watchlist. 
    You can add tickers to your watchlist and view their latest news and performance.
    """)

    st.title("Stock Ticker Lookup")

    # Create the searchbox
    selected_ticker = st_searchbox(
        search_symbols,
        placeholder="Type a company name (e.g. Apple)...",
        key="stock_search",
        clear_on_submit=True
    )
    print("Selected Ticker2:", selected_ticker)
    if selected_ticker:
        print("Selected Ticker:", selected_ticker)
        st.success(f"Selected Ticker: **{selected_ticker}**")
        if selected_ticker not in st.session_state.watchlist:
            print('Adding to watchlist')
            st.session_state.watchlist.append(selected_ticker)
            selected_ticker = None  # Clear the selection after adding
            st.rerun()  # Refresh to show the updated watchlist
    
    selected_to_remove = st.pills(
        label="Watchlist",
        options=st.session_state.watchlist,
        selection_mode="single",
        label_visibility="collapsed"
    )
    if selected_to_remove:
        print('Delete here')
        st.session_state.watchlist.remove(selected_to_remove)
        st.rerun()

##### clear all selected

    # updated_watchlist =st.multiselect(
    #     "Your Watchlist (multi-select)",
    #     options = st.session_state.watchlist,
    #     default = st.session_state.watchlist, # Show all as selected by default
    #     key="watchlist_multiselect", 
    #     on_change=onMultiselectChange,
    # )

  
    # st.multiselect(
    #     "Your Watchlist (multi-select)",
    #     options = st.session_state.watchlist,
    #     default = st.session_state.watchlist, # Show all as selected by default
    # )

    st.write("Current Watchlist:", st.session_state.watchlist)
    # if updated_watchlist != st.session_state.watchlist:
    #     st.session_state.watchlist = updated_watchlist
    #     st.rerun()
    # st.rerun()
#     cols = st.columns([4, 1])
#     new_ticker = cols[0].text_input("ADD TICKER E.G. MSFT", label_visibility="collapsed", placeholder="ADD TICKER E.G. MSFT")

#     if cols[1].button("+ Add", use_container_width=True):
#         if new_ticker and new_ticker not in st.session_state.watchlist:
#             st.session_state.watchlist.append(new_ticker.upper())
#             st.rerun()
#     selected_to_remove = st.pills("Your Watchlist (Click to remove):", 
#         options=st.session_state.watchlist,
#         selection_mode="single", # We use this to detect a 'click' to delete
#         label_visibility="collapsed",
# )
#     if selected_to_remove:
#         st.session_state.watchlist.remove(selected_to_remove)
#         st.rerun()
    # Display the result
