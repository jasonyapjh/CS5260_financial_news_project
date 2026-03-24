import streamlit as st
from utils.database import get_user_watchlist, update_ticker_status

def inject_custom_css(watchlist_data):
    """Generates and injects dynamic CSS for ticker buttons."""
    style_blocks = ""
    for ticker, info in watchlist_data.items():
        is_active = info.get("active", False)
        current_bg = "#00d4ff" if is_active else "#FF4B4B"
        hover_bg = "#00b8e6" if is_active else "#FF2B2B"
        safe_ticker = ticker.replace(".", "\\.").replace("-", "\\-")

        style_blocks += f"""
            .st-key-{safe_ticker} button {{
                background-color: {current_bg} !important;
                color: white !important;
                border-radius: 20px !important;
                font-weight: bold !important;
                font-size: 25px !important;
                border: 1px solid {current_bg} !important;
                width: 100% !important;
                min-height: 65px !important;
                width: 260px !important;
                transition: all 0.3s ease !important;
                box-shadow: 0 0 10px {current_bg}66 !important;
            }}
            .st-key-{safe_ticker} [data-testid="stMarkdownContainer"] p {{
                font-size: 20px !important;
                font-weight: 800 !important;
                line-height: 1.2 !important;
                margin: 0 !important;
            }}
            .st-key-{safe_ticker} button:hover {{
                background-color: {hover_bg} !important;
                box-shadow: 0 0 20px {current_bg}aa !important;
                transform: scale(1.02);
            }}
        """
    st.markdown(f"<style>{style_blocks}</style>", unsafe_allow_html=True)

def show():
    st.title("📰 Financial News Digest")
    st.caption("Generate AI-powered news digests for your stock watchlist")

    # 1. Sync & Initialize Watchlist State
    st.session_state.watchlist = get_user_watchlist(0)
    
    # 2. Layout Container
    with st.container(border=True):
        st.subheader("Generate New Digest")
        
        if not st.session_state.watchlist:
            st.warning("⚠️ Your watchlist is empty. Add tickers to get started.")
            return

        # Inject styles based on current state
        inject_custom_css(st.session_state.watchlist)

        # 3. Render Ticker Grid (4 Columns)
        tickers = list(st.session_state.watchlist.keys())
        rows = [tickers[i:i + 4] for i in range(0, len(tickers), 4)]

        for row in rows:
            cols = st.columns(4)
            for i, ticker in enumerate(row):
                info = st.session_state.watchlist[ticker]
                is_active = info.get("active", False)
                
                label = f"{'ACTIVE' if is_active else 'INACTIVE'}: {ticker}"
                icon = "check_circle" if is_active else "cancel"
                
                with cols[i]:
                    if st.button(f"{label} :material/{icon}:", key=ticker):
                        # Toggle State
                        new_status = not is_active
                        st.session_state.watchlist[ticker]["active"] = new_status
                        update_ticker_status(0, ticker, new_status)
                        st.rerun()

        st.divider()

        # 4. Action Section
        active_tickers = [t for t, info in st.session_state.watchlist.items() if info.get("active")]
        
        if active_tickers:
            st.success(f"Selected: **{', '.join(active_tickers)}**")
            if st.button("⚡ Generate Digest", use_container_width=True, type="primary"):
                st.info("Starting AI analysis... this may take a moment.")
        else:
            st.button("⚡ Generate Digest", use_container_width=True, type="primary", disabled=True)







# import streamlit as st
# from utils.database import (
#     get_user_watchlist, update_ticker_status
# )

# def show():
#     st.title("📰 Financial News Digest")
#     st.markdown("Generate AI-powered news digests for your stock watchlist")
    
#     with st.container(border=True):
#         st.subheader("Generate New Digest")

#         watchlist = get_user_watchlist(0)
    
#         if watchlist:
#             for ticker, info in watchlist.items():
#                 st.session_state.watchlist[ticker] = {"active" : True if info.get('active') else False}

#         ticker_list = list(st.session_state.watchlist.keys())
            
#         rows = [ticker_list[i:i + 4] for i in range(0, len(ticker_list), 4)]
        
#         style_blocks = ""
#         for ticker, info in st.session_state.watchlist.items():
#             is_active = info.get("active", False) if isinstance(info, dict) else info
#             current_bg = "#00d4ff" if is_active else "#FF4B4B"
#             hover_bg = "#00b8e6" if is_active else "#FF2B2B"

#             safe_ticker = ticker.replace(".", "\\.").replace("-", "\\-")
#             # We target the button specifically by its key
#             style_blocks += f"""
#                 div[data-testid="stElementContainer"]:has(div.stButton > button) {{
#                     /* This ensures the container doesn't restrict the button size */
#                     width: 250px !important;
#                 }}

#                 .st-key-{safe_ticker} button {{
#                     background-color: {current_bg} !important;
#                     color: white !important;
#                     border-radius: 20px !important;
#                     padding: 10px 25px !important;
#                     font-weight: bold !important;
#                     font-size: 25px !important;
#                     border: 1px solid {current_bg} !important;
#                     width: 260px !important;
#                     min-height: 60px !important;
#                     transition: all 0.3s ease !important;
#                     box-shadow: 0 0 10px {current_bg}66 !important;
#                 }}
            
#                 .st-key-{safe_ticker} [data-testid="stMarkdownContainer"] p {{
#                     font-size: 23px !important; /* Change this to your desired size */
#                     font-weight: 800 !important;
#                     color: white !important;
#                     line-height: 1 !important;
#                     margin: 0 !important;
#                 }}
#                 .st-key-{safe_ticker} button:hover {{
#                     background-color: {hover_bg} !important;
#                     box-shadow: 0 0 20px {current_bg}aa !important;
#                     border-color: white !important;
#                 }}
#             """
        
#         # Inject the final combined style block
#         st.markdown(f"<style>{style_blocks}</style>", unsafe_allow_html=True)



#         for row_tickers in rows:
#             # Create up to 4 columns for this specific row
#             cols = st.columns(4)

#             for i, ticker in enumerate(row_tickers):
#                 info = st.session_state.watchlist[ticker]
#                 is_active = info.get("active", False) if isinstance(info, dict) else info
#                 label = f"{'ACTIVE' if is_active else 'INACTIVE'}: {ticker}"
#                 icon = ":material/check_circle:" if is_active else ":material/cancel:"
                    
#                 with cols[i]:
#                     # The 'key' here MUST match the one in the CSS selector above
#                     if st.button(f"{label} {icon}", key=ticker):
#                         if isinstance(st.session_state.watchlist[ticker], dict):
#                             new_status = not is_active
#                             st.session_state.watchlist[ticker]["active"] = new_status
#                             update_ticker_status(user_id=0, ticker=ticker, status=new_status)
#                         else:
#                             st.session_state.watchlist[ticker] = not is_active
                      
#                         st.rerun()

#         # 4. Agent Status
#         active_list = [t for t, info in st.session_state.watchlist.items() 
#                     if (info.get("active", False) if isinstance(info, dict) else info)]
        
#         if active_list:
#             st.info(f"Agents are currently analyzing: **{', '.join(active_list)}**")
#         else:
#             st.warning(
#             "⚠️ Your watchlist is empty. "
#            #"[Add tickers in the Watchlist section](/?streamlit_pages=watchlist) to generate digests."
#         )

#         generate_button = st.button(
#                 "⚡ Generate Digest",
#                 use_container_width=True,
#                 type="primary"
#             )
#         # st.write(st.session_state.watchlist)