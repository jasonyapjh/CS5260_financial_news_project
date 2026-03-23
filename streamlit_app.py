import streamlit as st
import yfinance as yf


from streamlit_option_menu import option_menu

#from utils.helper import search_symbols
from utils.session import init_session
from dotenv import load_dotenv

# Import page modules
from pages import watchlist
# Load environment variables 
load_dotenv()


st.set_page_config(
    page_title="Financial News Intelligence",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_session()


#### TEMP ADD THIS
#st.session_state.watchlist = []
#st.session_state.watchlist.append("AAPL")

####
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

with st.sidebar:
    st.title("📰 Financial News Intelligence")
    st.markdown("---")
    
    selected = option_menu(
        menu_title=None,      # Name of the menu
        options=["Dashboard", "News Analysis", "Portfolio", "Watchlist", "Settings"], 
        icons=["house", "newspaper", "briefcase", "search", "gear"], 
        menu_icon="cast",            # Icon for the menu title
        default_index=0,             # Default page

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
if selected == "Dashboard":
    print('Test1')
    #digest.show()
elif selected == "Watchlist":
    print('Test2')
    watchlist.show()
elif selected == "Digest History":
    print('Test3')
    #history.show()
elif selected == "Settings":
    print('Test4')
   # settings.show()

# st.title("Stock Ticker Lookup")

# # Create the searchbox
# selected_ticker = st_searchbox(
#     search_symbols,
#     placeholder="Type a company name (e.g. Apple)...",
#     key="stock_search",
# )

# # Display the result
# if selected_ticker:
#     st.success(f"Selected Ticker: **{selected_ticker}**")
    
    # Optional: Show more info using the ticker
    # ticker_info = yf.Ticker(selected_ticker).info
    # st.write(f"Current Price: ${ticker_info.get('currentPrice')}")

# st.title("Financial News Intelligence")



# st.write("Current Watchlist:", st.session_state.watchlist)


# Footer
st.markdown("---")
st.markdown(
    """
    <div style="color: #888; 
    font-size: 0.9rem;  
    position: fixed;
    left: 0;
    bottom: 0;
    text-align: center;
    width: 100%;">
    Financial News Intelligence v1.0 | Powered by LangGraph & Streamlit
    </div>
    """,
    unsafe_allow_html=True
)
