"""
FinTel — Agentic Financial News Intelligence
Streamlit UI: runs the LangGraph pipeline in-process with live step updates.

Run:
    streamlit run app.py
"""

import sys
import os
import time
import json
from datetime import datetime

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Page config (must be first Streamlit call) ─────────────────────────────────
st.set_page_config(
    page_title="FinTel · Financial Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

/* Global */
html, body, [class*="css"] { font-family: 'Syne', sans-serif !important; }

/* Hide default Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0e1419 !important;
    border-right: 1px solid #1e2d3d !important;
}
section[data-testid="stSidebar"] * { color: #d4dde8 !important; }
section[data-testid="stSidebar"] .stTextInput input,
section[data-testid="stSidebar"] .stTextInput input[type=password] {
    background: #141c24 !important;
    border: 1px solid #1e2d3d !important;
    color: #d4dde8 !important;
    font-family: 'JetBrains Mono', monospace !important;
    border-radius: 4px !important;
}
section[data-testid="stSidebar"] .stButton button {
    background: transparent !important;
    border: 1px solid #00c8ff !important;
    color: #00c8ff !important;
    border-radius: 4px !important;
    font-weight: 700 !important;
    transition: background .2s !important;
}
section[data-testid="stSidebar"] .stButton button:hover {
    background: rgba(0,200,255,.1) !important;
}

/* Main area */
.main { background: #080c10; }
.stApp { background: #080c10; }

/* Metric cards */
div[data-testid="metric-container"] {
    background: #0e1419;
    border: 1px solid #1e2d3d;
    border-radius: 6px;
    padding: 14px 18px;
}
div[data-testid="metric-container"] label { color: #4a5a6a !important; font-size: 11px !important; text-transform: uppercase; letter-spacing: 1px; font-family: 'JetBrains Mono', monospace !important; }
div[data-testid="metric-container"] [data-testid="stMetricValue"] { color: #d4dde8 !important; font-family: 'JetBrains Mono', monospace !important; font-size: 26px !important; font-weight: 700 !important; }

/* Expander (event cards) */
details {
    background: #0e1419 !important;
    border: 1px solid #1e2d3d !important;
    border-radius: 6px !important;
    margin-bottom: 8px !important;
}
details[open] { border-color: #1e2d3d !important; }
summary {
    padding: 12px 16px !important;
    color: #d4dde8 !important;
    font-weight: 600 !important;
    cursor: pointer !important;
}

/* Progress bar color */
div[data-testid="stProgress"] > div > div > div { background: linear-gradient(90deg, #00c8ff, #00e5a0) !important; }

/* Tabs */
button[data-baseweb="tab"] { font-family: 'Syne', sans-serif !important; font-weight: 600 !important; color: #4a5a6a !important; }
button[data-baseweb="tab"][aria-selected="true"] { color: #00c8ff !important; border-bottom-color: #00c8ff !important; }

/* Code / mono spans */
code { font-family: 'JetBrains Mono', monospace !important; font-size: 12px !important; }

/* Divider */
hr { border-color: #1e2d3d !important; }

/* Info / success / error boxes */
div[data-testid="stAlert"] { border-radius: 4px !important; }
</style>
""", unsafe_allow_html=True)


# ── Constants ──────────────────────────────────────────────────────────────────
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


# ── Session state defaults ─────────────────────────────────────────────────────
def init_session():
    defaults = {
        "tickers": ["AAPL", "NVDA", "TSLA"],
        "pipeline_result": None,
        "running": False,
        "step_logs": [],
        "current_step": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📈 FinTel")
    st.markdown(
        "<span style='font-family:JetBrains Mono;font-size:11px;color:#4a5a6a;letter-spacing:1px'>AGENTIC FINANCIAL INTELLIGENCE</span>",
        unsafe_allow_html=True,
    )
    st.divider()

    # API Keys
    st.markdown("**🔑 API Keys**")
    openai_key  = st.text_input("OpenAI API Key",  type="password", placeholder="sk-...",    key="openai_key_input")
    newsapi_key = st.text_input("NewsAPI Key",      type="password", placeholder="abc123...", key="newsapi_key_input")

    st.divider()

    # Watchlist management
    st.markdown("**📊 Stock Watchlist**")
    col_inp, col_btn = st.columns([3, 1])
    with col_inp:
        new_ticker = st.text_input("", placeholder="e.g. MSFT", label_visibility="collapsed", key="new_ticker_input").upper().strip()
    with col_btn:
        st.markdown("<div style='margin-top:4px'>", unsafe_allow_html=True)
        if st.button("＋", use_container_width=True):
            t = new_ticker.replace(" ", "")
            if t and t not in st.session_state.tickers and len(st.session_state.tickers) < 10:
                st.session_state.tickers.append(t)
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # Chips
    if st.session_state.tickers:
        cols = st.columns(min(len(st.session_state.tickers), 3))
        for i, ticker in enumerate(st.session_state.tickers):
            with cols[i % 3]:
                if st.button(f"{ticker} ✕", key=f"rm_{ticker}", use_container_width=True):
                    st.session_state.tickers.remove(ticker)
                    st.rerun()

    st.divider()

    # Run button
    run_disabled = (
        st.session_state.running
        or not openai_key
        or not newsapi_key
        or not st.session_state.tickers
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

    if st.session_state.pipeline_result:
        if st.button("↺  New Run", use_container_width=True):
            st.session_state.pipeline_result = None
            st.session_state.running = False
            st.session_state.step_logs = []
            st.session_state.current_step = 0
            st.rerun()

    st.divider()
    st.markdown(
        "<span style='font-size:11px;color:#4a5a6a;font-family:JetBrains Mono'>OpenAI GPT-4o · LangGraph<br>NewsAPI · Streamlit</span>",
        unsafe_allow_html=True,
    )


# ── Main area ──────────────────────────────────────────────────────────────────

# Header
st.markdown(
    f"""
    <div style='margin-bottom:24px'>
      <h1 style='font-size:32px;font-weight:800;color:#f1f5f9;letter-spacing:-1px;margin:0'>
        Financial News <span style='color:#00c8ff'>Intelligence</span>
      </h1>
      <p style='color:#4a5a6a;font-family:JetBrains Mono;font-size:12px;margin-top:4px'>
        7-Agent LangGraph Pipeline &nbsp;·&nbsp; Watchlist: {" · ".join(st.session_state.tickers) or "None"}
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ══════════════════════════════════════════════════════════════════════
# RUNNING — execute pipeline and show live progress
# ══════════════════════════════════════════════════════════════════════
if st.session_state.running and not st.session_state.pipeline_result:
    st.markdown("### ⚙️ Pipeline Executing")
    overall_progress = st.progress(0, text="Starting pipeline…")

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
            name_slot = st.empty()
            log_slot  = st.empty()
            name_slot.markdown(f"<span style='color:#4a5a6a;font-weight:600'>{name}</span>", unsafe_allow_html=True)
            log_slot.markdown("<span style='font-size:11px;color:#2a3a4a;font-family:JetBrains Mono'>Waiting…</span>", unsafe_allow_html=True)
        step_containers.append((icon_slot, name_slot, log_slot))

    log_box = st.empty()

    # Monkey-patch agents to update UI in real time
    import agents.watchlist_agent     as _wa
    import agents.retrieval_agent     as _ra
    import agents.filter_agent        as _fa
    import agents.clustering_agent    as _ca
    import agents.summarization_agent as _sa
    import agents.ranking_agent       as _rka
    import agents.notification_agent  as _na

    _originals = {
        "watchlist":     _wa.watchlist_agent,
        "retrieval":     _ra.retrieval_agent,
        "filter":        _fa.filter_agent,
        "clustering":    _ca.clustering_agent,
        "summarization": _sa.summarization_agent,
        "ranking":       _rka.ranking_agent,
        "notification":  _na.notification_agent,
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
            log_slot.markdown("<span style='font-size:11px;color:#00c8ff;font-family:JetBrains Mono'>Running…</span>", unsafe_allow_html=True)
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
                    f"<span style='font-size:11px;color:#22c55e;font-family:JetBrains Mono'>{last}</span>",
                    unsafe_allow_html=True,
                )
                st.session_state.step_logs = logs

            overall_progress.progress(step_idx / 7, text=f"Agent {step_idx}/7 complete")
            return result
        return wrapper

    _wa.watchlist_agent     = make_wrapper(_originals["watchlist"],     1)
    _ra.retrieval_agent     = make_wrapper(_originals["retrieval"],     2)
    _fa.filter_agent        = make_wrapper(_originals["filter"],        3)
    _ca.clustering_agent    = make_wrapper(_originals["clustering"],    4)
    _sa.summarization_agent = make_wrapper(_originals["summarization"], 5)
    _rka.ranking_agent      = make_wrapper(_originals["ranking"],       6)
    _na.notification_agent  = make_wrapper(_originals["notification"],  7)

    try:
        from pipeline import run_pipeline
        result = run_pipeline(
            watchlist=st.session_state.tickers,
            openai_key=openai_key,
            newsapi_key=newsapi_key,
        )

        if result.get("error"):
            st.error(f"Pipeline error: {result['error']}")
            st.session_state.running = False
        else:
            overall_progress.progress(1.0, text="✓ Pipeline complete!")
            st.session_state.pipeline_result = result
            st.session_state.running = False

    except Exception as e:
        st.error(f"Unexpected error: {e}")
        st.session_state.running = False

    finally:
        # Always restore originals
        _wa.watchlist_agent     = _originals["watchlist"]
        _ra.retrieval_agent     = _originals["retrieval"]
        _fa.filter_agent        = _originals["filter"]
        _ca.clustering_agent    = _originals["clustering"]
        _sa.summarization_agent = _originals["summarization"]
        _rka.ranking_agent      = _originals["ranking"]
        _na.notification_agent  = _originals["notification"]

    if st.session_state.pipeline_result:
        time.sleep(0.5)
        st.rerun()


# ══════════════════════════════════════════════════════════════════════
# RESULTS
# ══════════════════════════════════════════════════════════════════════
elif st.session_state.pipeline_result:
    result = st.session_state.pipeline_result
    digest = result.get("digest", {})
    high   = digest.get("high",   [])
    medium = digest.get("medium", [])
    low    = digest.get("low",    [])
    all_events = high + medium + low

    # ── Summary metrics ──────────────────────────────────────────────
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
                file_name=f"fintel_digest_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
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


# ══════════════════════════════════════════════════════════════════════
# LANDING / IDLE
# ══════════════════════════════════════════════════════════════════════
else:
    # Architecture overview
    st.markdown("### 🏗️ Pipeline Architecture")
    st.markdown(
        "<p style='color:#4a5a6a;font-family:JetBrains Mono;font-size:12px'>"
        "OpenAI GPT-4o · LangGraph StateGraph · 7 specialized agents</p>",
        unsafe_allow_html=True,
    )

    steps = [
        ("Watchlist & Context Agent",    "Expands tickers into structured query bundles with aliases and industry context"),
        ("News Retrieval Agent",         "Fetches candidate articles from NewsAPI across all company and industry queries"),
        ("Noise Filter & Dedup Agent",   "Heuristic + GPT-4o semantic deduplication; removes low-signal content"),
        ("Event Clustering Agent",       "Groups related articles into typed event clusters (earnings, M&A, regulation…)"),
        ("Impact Summarization Agent",   "Generates TLDR, key bullets, investment impact + verification pass"),
        ("Importance Ranking Agent",     "Blended heuristic + GPT-4o importance scoring: High / Medium / Low"),
        ("Digest Packaging Agent",       "Renders curated HTML email digest with source links and uncertainty flags"),
    ]

    STEP_COLORS = ["#00c8ff","#5a9fd4","#9b5de5","#f72585","#ef4444","#f97316","#22c55e"]

    for i, (name, desc) in enumerate(steps):
        col_num, col_body, col_arrow = st.columns([1, 10, 1])
        with col_num:
            st.markdown(
                f"<div style='width:36px;height:36px;border-radius:50%;"
                f"border:1px solid {STEP_COLORS[i]};background:{STEP_COLORS[i]}18;"
                f"display:flex;align-items:center;justify-content:center;"
                f"font-family:JetBrains Mono;font-size:13px;font-weight:700;color:{STEP_COLORS[i]}'>{i+1}</div>",
                unsafe_allow_html=True,
            )
        with col_body:
            st.markdown(
                f"<div style='padding:10px 14px;background:#0e1419;border:1px solid #1e2d3d;"
                f"border-radius:4px;margin-bottom:4px'>"
                f"<span style='font-weight:700;color:#f1f5f9'>{name}</span><br>"
                f"<span style='font-size:12px;color:#4a5a6a;font-family:JetBrains Mono'>{desc}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with col_arrow:
            if i < len(steps) - 1:
                st.markdown(
                    "<div style='text-align:center;color:#1e2d3d;font-size:18px;margin-top:8px'>↓</div>",
                    unsafe_allow_html=True,
                )

    st.divider()
    st.info("👈  Enter your API keys and watchlist in the sidebar, then click **Run Pipelines**.")
