import streamlit as st
import yfinance as yf


from streamlit_option_menu import option_menu

#from utils.helper import search_symbols
from utils.session import init_session
from dotenv import load_dotenv

# Import page modules
from streamlit_pages import watchlist
from streamlit_pages import settings

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

####


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
    st.pills("Watchlist", options=['Test1', 'Test2'], label_visibility="collapsed")
    #digest.show()
elif selected == "Watchlist":
    watchlist.show()
# elif selected == "Digest History":
#     print('Test3')
    #history.show()
elif selected == "Settings":
    settings.show()

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
