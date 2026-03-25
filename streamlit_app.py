import streamlit as st
import yfinance as yf


from streamlit_option_menu import option_menu
from streamlit_elements import elements, mui, html
#from utils.helper import search_symbols
from utils.session import init_session
from utils.database import init_db
from dotenv import load_dotenv

# Import page modules
from streamlit_pages import watchlist
from streamlit_pages import settings
from streamlit_pages import dashboard


# Load environment variables 
load_dotenv()


st.set_page_config(
    page_title="Financial News Intelligence",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_session()

init_db()


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
    
    # # User info
    # if "user_id" in st.session_state:
    #     st.markdown(f"**User ID:** {st.session_state.user_id}")
    
    # st.markdown("---")
    st.markdown("""
    **About this app:**
    
    This application uses a 7-agent AI pipeline to:
    1. Retrieve news for your stock tickers
    2. Cluster and summarize events
    3. Rank by importance
    4. Generate curated digests
    
    **Supported LLM Providers:**
    - OpenAI (GPT-4o)
    """)

# Main content area
if selected == "Dashboard":
    dashboard.show()
elif selected == "Watchlist":
    watchlist.show()
elif selected == "News Analysis":
    st.markdown("""
    <style>
    div.stButton > button {
        background-color: #00d4ff !important;
        color: white !important;
        border-radius: 20px !important;
        padding: 10px 25px !important;
        font-weight: bold !important;
        border: none !important;
        width: 200px !important;
        box-shadow: 0 0 10px rgba(0, 212, 255, 0.4);
    }
    div.stButton > button:hover {
        background-color: #00b8e6 !important;
        box-shadow: 0 0 20px rgba(0, 212, 255, 0.6);
    }
    </style>
    """, unsafe_allow_html=True)

    # 2. Use a standard button (it will inherit the style above)
    if st.button("Analyze AAPL :material/chat:"):
        st.write("Analyzing AAPL news...22")
    
elif selected == "Settings":
    settings.show()



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
