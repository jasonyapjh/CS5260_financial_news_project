import streamlit as st
from utils.database import get_user_watchlist, update_ticker_status

from utils.llm import call_openai_test
import json
import time


# =================================
# ---Constant----------------------
# =================================
STEP_NAMES = [
    "Watchlist & Context Agent",
    "News Retrieval Agent",
    "Noise Filter & Dedup Agent",
    "Event Clustering Agent",
    "Impact Summarization Agent",
    "Importance Ranking Agent",
    "Digest Packaging Agent",
]

# =================================
# ---Custom CSS--------------------
# =================================
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
                border-radius: 10px !important;
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
            cols = st.columns(5)
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
        st.success(f"Selected: **{', '.join(active_tickers)}**")
        # Run button
        run_disabled = (
            st.session_state.running
            # or not openai_key
            # or not newsapi_key
            or not active_tickers
        )

        if st.button(
            "⚡  Run Pipeline" if not st.session_state.running else "⏳  Running...",
            use_container_width=True,
            disabled=run_disabled,
            type="primary",
        ):
            st.session_state.running = True
            st.session_state.pipeline_result = None
            st.session_state.step_logs = []
            st.session_state.current_step = 0
            st.rerun()
# ══════════════════════════════════════════════════════════════════════
# RUNNING — execute pipeline and show live progress
# ══════════════════════════════════════════════════════════════════════
    if st.session_state.running and not st.session_state.pipeline_result:
        st.info("Starting AI analysis... this may take a moment.")
        # Progress tracking
        status_text = st.empty()
        overall_progress = st.progress(0, text="Starting pipeline…")
        #agent_info = st.empty()

        step_containers = []
        for i, name in enumerate(STEP_NAMES):
            col_icon, col_body = st.columns([1, 11])
            with col_icon:
                icon_slot = st.empty()
                icon_slot.markdown(
                    f"<div style='width:32px;height:32px;border-radius:50%;border:1px solid #1e2d3d;"
                    f"display:flex;align-items:center;justify-content:center;"
                    f"font-family:JetBrains Mono;font-size:12px;color:#4a5a6a;background:#0e1419'>{i+1}</div>",
                    unsafe_allow_html=True,
                )
            with col_body:
                c1, c2 = st.columns([1,3])
                with c1:
                    name_slot = st.empty()
                    name_slot.markdown(f"<span style='color:#4a5a6a;font-weight:600;margin:0;'>{name}</span>", unsafe_allow_html=True)
                with c2:
                    log_slot  = st.empty()
                    log_slot.markdown("<span style='font-size:15px;color:#2a3a4a;'>Waiting…</span>", unsafe_allow_html=True)
            step_containers.append((icon_slot, name_slot, log_slot))

        log_box = st.empty()



        import agents.watchlist_agent as wa
        import agents.retrieval_agent as ra
        _originals = {
            "watchlist": wa.watchlist_agent,
            "retrieval": ra.retrieval_agent,
        }

        def make_wrapper(fn, step_idx):
            def wrapper(state):
                # Mark active
                icon_slot, name_slot, log_slot = step_containers[step_idx - 1]
                icon_slot.markdown(
                    f"<div style='width:32px;height:32px;border-radius:50%;"
                    f"border:1px solid #00c8ff;background:rgba(0,200,255,.1);"
                    f"display:flex;align-items:center;justify-content:center;"
                    f"font-family:JetBrains Mono;font-size:12px;color:#00c8ff'>{step_idx}</div>",
                    unsafe_allow_html=True,
                )
                name_slot.markdown(f"<span style='color:#f1f5f9;font-weight:700'>{STEP_NAMES[step_idx-1]}</span>", unsafe_allow_html=True)
                log_slot.markdown("<span style='font-size:12px;color:#00c8ff;'>Running…</span>", unsafe_allow_html=True)
                overall_progress.progress(
                    (step_idx - 1) / 7,
                    text=f"Agent {step_idx}/7: {STEP_NAMES[step_idx-1]}",
                )

                result = fn(state)

                # Mark done
                icon_slot.markdown(
                    f"<div style='width:32px;height:32px;border-radius:50%;"
                    f"border:1px solid #22c55e;background:#22c55e;"
                    f"display:flex;align-items:center;justify-content:center;"
                    f"font-size:14px;color:#000'>✓</div>",
                    unsafe_allow_html=True,
                )
                name_slot.markdown(f"<span style='color:#22c55e;font-weight:700'>{STEP_NAMES[step_idx-1]}</span>", unsafe_allow_html=True)

                # Show latest log line
                logs = result.get("step_logs", [])
                if logs:
                    last = logs[-1]
                    log_slot.markdown(
                        f"<span style='font-size:15px;color:#22c55e;'>{last}</span>",
                        unsafe_allow_html=True,
                    )
                    st.session_state.step_logs = logs
                print(logs)
                overall_progress.progress(step_idx / 7, text=f"Agent {step_idx}/7 complete")
                return result
            return wrapper
        
        wa.watchlist_agent     = make_wrapper(_originals["watchlist"],     1)
        ra.retrieval_agent     = make_wrapper(_originals["retrieval"],     2)


        try:
            status_text.info("🔄 Starting pipeline execution...")

            from agents.pipeline import run_pipeline
            result = run_pipeline(watchlist=active_tickers, openai_key='')

            
            if result.get("error"):
                st.error(f"Pipeline error: {result['error']}")
                st.session_state.running = False
            else:
                time.sleep(2)
                overall_progress.progress(1.0, text="✓ Pipeline complete!")
                st.session_state.pipeline_result = result
                st.session_state.running = False

                # output_path = "agent_1_output.json"
                # with open(output_path, "w") as f:
                #     json.dump( st.session_state.pipeline_result, f, indent=4)

        except Exception as e:
            status_text.error(f"✗ Error: {str(e)}")
            st.session_state.running = False
        finally:
                # Always restore originals
                wa.watchlist_agent = _originals["watchlist"]
                ra.retrieval_agent = _originals["retrieval"]
        if st.session_state.pipeline_result:
            time.sleep(0.5)
            st.rerun()

    elif st.session_state.pipeline_result:
        result = st.session_state.pipeline_result 







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