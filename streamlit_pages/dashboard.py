import streamlit as st
from utils.database import get_user_watchlist, update_ticker_status

from utils.llm import call_openai_test
import json
import time
import datetime as datetime

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
PRIORITY_COLORS = {"High": "#ef4444", "Medium": "#f97316", "Low": "#22c55e"}
PRIORITY_BG     = {"High": "#2a0a0a", "Medium": "#2a1400", "Low": "#0a2014"}
SENTIMENT_EMOJI = {"bullish": "▲", "bearish": "▼", "neutral": "◆"}
SENTIMENT_COLOR = {"bullish": "#22c55e", "bearish": "#ef4444", "neutral": "#fbbf24"}
EVENT_ICONS = {
    "earnings": "📊", "guidance": "🎯", "M&A": "🤝", "merger": "🤝",
    "acquisition": "🤝", "regulation": "⚖️", "litigation": "🏛️",
    "executive_change": "👤", "product_launch": "🚀", "analyst_rating": "⭐",
    "partnership": "🔗", "macro": "🌐", "market_trend": "📈", "other": "📌",
}
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
        #rows = [tickers[i:i + 4] for i in range(0, len(tickers), 4)]
        rows = [tickers[i:i + 2] for i in range(0, len(tickers), 2)]
        for row in rows:
            cols = st.columns(2)
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
        import agents.filter_agent as fa
        import agents.clustering_agent as ca
        import agents.summarization_agent as sa
        import agents.ranking_agent as rna
        import agents.notification_agent as na
        _originals = {
            "watchlist": wa.watchlist_agent,
            "retrieval": ra.retrieval_agent,
            "filter": fa.filter_agent,
            "cluster": ca.clustering_agent,
            "summarization": sa.summarization_agent,
            "ranking": rna.ranking_agent,
            "notification": na.notification_agent
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
        fa.filter_agent        = make_wrapper(_originals["filter"],        3)
        ca.clustering_agent    = make_wrapper(_originals["cluster"],       4)
        sa.summarization_agent = make_wrapper(_originals["summarization"], 5)
        rna.ranking_agent = make_wrapper(_originals["ranking"], 6)
        na.notification_agent = make_wrapper(_originals["notification"], 7)
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
                fa.filter_agent = _originals["filter"]
                ca.clustering_agent    = _originals["cluster"]
                sa.summarization_agent = _originals["summarization"]
                rna.ranking_agent = _originals["ranking"]
                na.notification_agent = _originals["notification"]
        if st.session_state.pipeline_result:
            time.sleep(0.5)
            st.rerun()

    elif st.session_state.pipeline_result:
        result = st.session_state.pipeline_result 
        digest = result.get("digest", {})
        high   = digest.get("high",   [])
        medium = digest.get("medium", [])
        low    = digest.get("low",    [])
        all_events = high + medium + low

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("📥 Articles Fetched",  result.get("raw_article_count", 0))
        c2.metric("🧹 After Filtering",   result.get("clean_article_count", 0))
        c3.metric("🗂 Total Events",       len(all_events))
        c4.metric("🔴 High Priority",      len(high))
        c5.metric("🟠 Medium Priority",    len(medium))
    
        generated = digest.get("generated_at", "")
        if generated:
            try:
                dt = datetime.fromisoformat(generated.replace("Z", "+00:00"))
                st.caption(f"Generated: {dt.strftime('%B %d, %Y  %H:%M UTC')}")
            except Exception:
                pass
    
        st.divider()
         # ── Filter tabs ──────────────────────────────────────────────────
        tab_all, tab_high, tab_med, tab_low, tab_digest, tab_logs = st.tabs([
            f"All  ({len(all_events)})",
            f"🔴 High  ({len(high)})",
            f"🟠 Medium  ({len(medium)})",
            f"🟢 Low  ({len(low)})",
            "📧 HTML Digest",
            "📋 Pipeline Logs",
        ])

        def render_event_card(e: dict):
            """Render a single event as a styled Streamlit expander."""
            label = e.get("importance_label", "Low")
            sent  = e.get("sentiment", "neutral")
            etype = e.get("event_type", "other")
            icon  = EVENT_ICONS.get(etype, "📌")
            pcolor = PRIORITY_COLORS.get(label, "#22c55e")
            pbg    = PRIORITY_BG.get(label, "#0a2014")
            scolor = SENTIMENT_COLOR.get(sent, "#fbbf24")
            semoji = SENTIMENT_EMOJI.get(sent, "◆")
            tickers_str = "  ".join(f"`{t}`" for t in e.get("tickers_affected", []))
            score = e.get("importance_score", 0)
    
            header = (
                f"{icon} **{e.get('event_title', '')}** &nbsp;&nbsp;"
                f"<span style='color:{pcolor};font-size:12px;font-weight:700;background:{pbg};"
                f"padding:2px 8px;border-radius:3px;border:1px solid {pcolor}33'>{label}</span>"
                f"&nbsp;<span style='color:{scolor};font-size:12px'>{semoji} {sent}</span>"
            )
            with st.expander(f"{icon}  {e.get('event_title', '')}  ·  {label}  ·  {sent.capitalize()}", expanded=False):
                # Meta row
                col_meta, col_score = st.columns([4, 1])
                with col_meta:
                    st.markdown(
                        f"**Tickers:** {tickers_str} &nbsp;·&nbsp; "
                        f"**Type:** `{etype.replace('_',' ').title()}` &nbsp;·&nbsp; "
                        f"**Sources:** {e.get('article_count', 0)}"
                    )
                with col_score:
                    st.markdown(
                        f"<div style='text-align:right;font-family:JetBrains Mono;font-size:22px;"
                        f"font-weight:700;color:{pcolor}'>{score}<span style='font-size:12px;color:#4a5a6a'>/10</span></div>",
                        unsafe_allow_html=True,
                    )
    
                st.divider()
    
                # TLDR
                st.markdown(f"**TLDR:** {e.get('tldr', '')}")
    
                # Bullets
                bullets = e.get("key_bullets", [])
                if bullets:
                    st.markdown("**Key Facts:**")
                    for b in bullets:
                        st.markdown(f"- {b}")
    
                # Investment impact
                impact = e.get("investment_impact", "")
                if impact:
                    st.markdown(
                        f"""<div style='background:#0a1f10;border:1px solid #1a4a2a;border-radius:6px;
                        padding:12px 16px;margin:12px 0'>
                        <div style='font-size:10px;color:#22c55e;font-family:JetBrains Mono;
                        text-transform:uppercase;letter-spacing:1.5px;font-weight:700;margin-bottom:6px'>
                        💼 Investment Perspective</div>
                        <div style='font-size:14px;color:#9dd4b8;line-height:1.6'>{impact}</div>
                        </div>""",
                        unsafe_allow_html=True,
                    )
    
                # Ranking rationale
                rationale = e.get("importance_rationale", "")
                if rationale:
                    st.caption(f"📊 Ranked: {rationale}")
    
                # Uncertainty flags
                flags = [f for f in e.get("uncertainty_flags", []) if f]
                if flags:
                    st.warning("⚠️ " + " · ".join(flags))
    
                # Confidence & sources
                col_conf, col_src = st.columns([1, 3])
                with col_conf:
                    conf = e.get("confidence", "low")
                    conf_color = {"high": "#22c55e", "medium": "#fbbf24", "low": "#ef4444"}.get(conf, "#4a5a6a")
                    st.markdown(
                        f"<span style='font-family:JetBrains Mono;font-size:11px;color:{conf_color};"
                        f"background:{conf_color}1a;padding:3px 8px;border-radius:3px;"
                        f"border:1px solid {conf_color}44'>Confidence: {conf}</span>",
                        unsafe_allow_html=True,
                    )
                with col_src:
                    urls = [u for u in e.get("source_urls", []) if u]
                    if urls:
                        links = "  ".join(f"[Source {i+1}]({u})" for i, u in enumerate(urls[:3]))
                        st.markdown(links)

        def render_event_list(events):
            if not events:
                st.markdown(
                    "<div style='text-align:center;padding:40px;color:#4a5a6a'>No events in this category.</div>",
                    unsafe_allow_html=True,
                )
                return
            for e in events:
                render_event_card(e)
        
        with tab_all:
            render_event_list(all_events)
    
        with tab_high:
            render_event_list(high)
    
        with tab_med:
            render_event_list(medium)
    
        with tab_low:
            render_event_list(low)
    
        with tab_digest:
            html_content = digest.get("html", "")
            if html_content:
                # Save and offer download
                st.download_button(
                    label="⬇️  Download HTML Digest",
                    data=html_content,
                    file_name=f"fintel_digest_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.html",
                    mime="text/html",
                    use_container_width=True,
                )
                st.markdown("**Preview:**")
                st.components.v1.html(html_content, height=700, scrolling=True)
            else:
                st.info("No HTML digest available.")
    
        with tab_logs:
            st.markdown("**Pipeline execution logs:**")
            logs = st.session_state.step_logs
            if logs:
                log_text = "\n".join(logs)
                st.code(log_text, language="text")
                st.download_button(
                    "⬇️  Download Logs",
                    data=log_text,
                    file_name="fintel_logs.txt",
                    mime="text/plain",
                )
            else:
                st.info("No logs captured.")
    
            st.markdown("**Raw result JSON:**")
            safe_result = {
                k: v for k, v in result.items()
                if k not in ("openai_key", "newsapi_key", "digest")
            }
            safe_result["digest_summary"] = {
                "generated_at": digest.get("generated_at", ""),
                "high_count":   len(high),
                "medium_count": len(medium),
                "low_count":    len(low),
            }
            st.json(safe_result, expanded=False)


