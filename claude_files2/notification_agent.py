"""Agent 7: Notification & Email Packaging."""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone
from utils.state import PipelineState


PRIORITY_COLORS = {"High": "#ef4444", "Medium": "#f97316", "Low": "#22c55e"}
SENTIMENT_EMOJI = {"bullish": "▲", "bearish": "▼", "neutral": "◆"}
EVENT_ICONS = {
    "earnings":"📊","earnings_release":"📊",
    "guidance":"🎯","guidance_update":"🎯",
    "M&A":"🤝","ma_announcement":"🤝",
    "dividend":"💰",
    "capital_action":"🏦",
    "regulation":"⚖️","regulatory_action":"⚖️",
    "litigation":"🏛️",
    "executive_change":"👤","leadership_change":"👤",
    "product_launch":"🚀",
    "analyst_rating":"⭐",
    "partnership":"🔗",
    "macro":"🌐",
    "market_trend":"📈",
    "general_news":"📰",
    "other":"📌",
}


def _card_html(e: dict) -> str:
    color = PRIORITY_COLORS.get(e.get("importance","Low"), "#22c55e")
    icon = EVENT_ICONS.get(e.get("event_type","other"), "📌")
    sent_emoji = SENTIMENT_EMOJI.get(e.get("sentiment","neutral"), "◆")
    tickers = e.get("ticker", "")
    bullets = "".join(f"<li style='margin:4px 0;color:#ccc'>{b}</li>" for b in e.get("key_facts",[]))
    urls = [u for u in e.get("source_urls",[]) if u][:3]
    refs = " ".join(f'<a href="{u}" style="color:#60a5fa;font-size:11px;margin-right:8px">source ↗</a>' for u in urls)
    flags = e.get("uncertainty_flags",[])
    flag_html = f'<div style="background:#422;padding:6px 10px;border-radius:4px;font-size:12px;color:#fbbf24;margin-top:8px">⚠ {"; ".join(flags)}</div>' if flags else ""
    return f"""
<div style="border:1px solid #333;border-left:3px solid {color};border-radius:8px;padding:16px;margin:10px 0;background:#1a1a1a">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px">
    <strong style="color:#f0f0f0;font-size:14px">{icon} {e.get("representative_headline", "") or e.get("tldr","")[:80]}</strong>
    <span style="color:{color};font-size:12px;font-weight:700;white-space:nowrap;margin-left:12px">{e.get("importance","")}</span>
  </div>
  <div style="font-size:12px;color:#666;margin-bottom:8px">{tickers} · {e.get("event_type","").replace("_"," ").title()} · {e.get("article_count",0)} sources · {sent_emoji} {e.get("sentiment","neutral")}</div>
  <p style="color:#ddd;font-size:13px;margin:0 0 8px 0">{e.get("tldr","")}</p>
  <ul style="margin:0 0 10px 16px;font-size:13px;padding:0">{bullets}</ul>
  <div style="background:#0f2a1a;border:1px solid #1a4a2a;border-radius:6px;padding:10px;font-size:13px;color:#86efac">
    <strong>💼 Investment Perspective</strong><br>{e.get("impact","")}
  </div>
  {flag_html}
  <div style="margin-top:8px">{refs}</div>
</div>"""


def notification_agent(state: PipelineState) -> PipelineState:
    state["current_step"] = 7
    state["step_logs"].append("[Agent 7] Packaging digest...")

    events = state.get("ranked_events", [])
    high   = [e for e in events if e.get("importance") == "High"]
    medium = [e for e in events if e.get("importance") == "Medium"]
    low    = [e for e in events if e.get("importance") == "Low"]

    now = datetime.now(timezone.utc)
    date_str = now.strftime("%B %d, %Y %H:%M UTC")
    tickers_str = ", ".join(state.get("watchlist", []))

    def section(title, color, evts):
        if not evts: return ""
        cards = "".join(_card_html(e) for e in evts)
        return f'<h2 style="color:{color};margin:24px 0 12px;font-size:16px;border-bottom:1px solid #333;padding-bottom:8px">{title} ({len(evts)})</h2>{cards}'

    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#111;color:#e0e0e0;max-width:780px;margin:0 auto;padding:24px">
<div style="background:linear-gradient(135deg,#0f172a,#1e293b);padding:24px;border-radius:12px;margin-bottom:24px;border:1px solid #334155">
  <h1 style="margin:0 0 6px;font-size:22px;color:#f1f5f9">📈 FinTel Intelligence Digest</h1>
  <div style="font-size:13px;color:#94a3b8">{tickers_str} &nbsp;·&nbsp; {date_str}</div>
  <div style="margin-top:12px;font-size:13px">
    <span style="background:rgba(239,68,68,.2);color:#ef4444;padding:3px 10px;border-radius:20px;margin-right:8px">⚡ {len(high)} High</span>
    <span style="background:rgba(249,115,22,.2);color:#f97316;padding:3px 10px;border-radius:20px;margin-right:8px">◉ {len(medium)} Medium</span>
    <span style="background:rgba(34,197,94,.2);color:#22c55e;padding:3px 10px;border-radius:20px">○ {len(low)} Low</span>
  </div>
</div>
{section("⚡ High Priority", "#ef4444", high)}
{section("◉ Medium Priority", "#f97316", medium)}
{section("○ Low Priority", "#22c55e", low)}
<div style="margin-top:32px;font-size:11px;color:#444;text-align:center">FinTel · OpenAI GPT-4o + LangGraph · Not financial advice</div>
</body></html>"""

    text_lines = [f"FinTel Digest — {tickers_str} — {date_str}", ""]
    for label, evts in [("HIGH", high), ("MEDIUM", medium), ("LOW", low)]:
        for e in evts:
            text_lines += [f"[{label}] {e.get('representative_headline', '') or e.get('tldr','')[:80]}", e.get("tldr",""), ""]

    os.makedirs("output", exist_ok=True)
    with open("output/digest.html", "w") as f:
        f.write(html)

    state["digest"] = {
        "generated_at": now.isoformat(),
        "high": high, "medium": medium, "low": low,
        "html": html, "text": "\n".join(text_lines),
    }
    state["step_logs"].append(f"[Agent 7] ✓ Digest ready — {len(high)} high, {len(medium)} medium, {len(low)} low")
    return state
