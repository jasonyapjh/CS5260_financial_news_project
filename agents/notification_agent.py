"""
agents/notification_agent.py
-----------------------------
Agent 7 — NotificationAgent

Packages ranked events into a digest dict containing:
  - high / medium / low event lists
  - A styled HTML email digest
  - A plain-text version
  - Saves digest.html to output/

Optional SMTP delivery via SMTP_HOST / SMTP_USER / SMTP_PASS env vars.
"""

from __future__ import annotations

import os
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from core.base_agent import BaseAgent
from core.state import PipelineState


PRIORITY_COLORS = {"High": "#ef4444", "Medium": "#f97316", "Low": "#22c55e"}
SENTIMENT_EMOJI = {"bullish": "▲", "bearish": "▼", "neutral": "◆"}
EVENT_ICONS = {
    "earnings_release": "📊", "earnings": "📊",
    "dividend":         "💰",
    "guidance_update":  "🎯", "guidance": "🎯",
    "ma_announcement":  "🤝", "M&A": "🤝",
    "regulatory_action":"⚖️", "regulation": "⚖️",
    "capital_action":   "🏦",
    "leadership_change":"👤", "executive_change": "👤",
    "litigation":       "🏛️",
    "product_launch":   "🚀",
    "analyst_rating":   "⭐",
    "partnership":      "🔗",
    "macro":            "🌐",
    "market_trend":     "📈",
    "general_news":     "📰",
    "other":            "📌",
}


class NotificationAgent(BaseAgent):
    """
    Agent 7: Packages ranked events into digest JSON + HTML email.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.min_importance = config.get("min_importance", "Low")
        self.output_dir     = config.get("output_dir", "output")

    def run(self, state: PipelineState) -> PipelineState:
        events = state.ranked_digest
        self.log_start(f"{len(events)} ranked events")
        state.current_step = 7
        state.step_logs.append("[Agent 7] Packaging digest...")

        high   = [e for e in events if e.get("importance") == "High"]
        medium = [e for e in events if e.get("importance") == "Medium"]
        low    = [e for e in events if e.get("importance") == "Low"]

        now      = datetime.now(timezone.utc)
        date_str = now.strftime("%B %d, %Y %H:%M UTC")
        tickers  = ", ".join(state.watchlist)

        html_content = self._render_html(tickers, date_str, high, medium, low)
        text_content = self._render_text(tickers, date_str, high, medium, low)

        # Persist HTML
        os.makedirs(self.output_dir, exist_ok=True)
        path = os.path.join(self.output_dir, "digest.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html_content)
        self.logger.info(f"HTML digest saved to {path}")

        state.ranked_digest = {
            "generated_at": now.isoformat(),
            "high":   high,
            "medium": medium,
            "low":    low,
            "html":   html_content,
            "text":   text_content,
        }
        msg = f"[Agent 7] ✓ Digest ready — {len(high)} High / {len(medium)} Medium / {len(low)} Low"
        state.step_logs.append(msg)
        self.log_done(msg)
        return state

    # ── HTML rendering ────────────────────────────────────────────────────────
    def _render_html(
        self,
        tickers: str,
        date_str: str,
        high: list[dict],
        medium: list[dict],
        low: list[dict],
    ) -> str:
        def section(title: str, color: str, events: list[dict]) -> str:
            if not events:
                return ""
            cards = "".join(self._card_html(e) for e in events)
            return (
                f'<h2 style="color:{color};margin:24px 0 12px;font-size:16px;'
                f'border-bottom:1px solid #333;padding-bottom:8px">'
                f'{title} ({len(events)})</h2>{cards}'
            )

        return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  background:#111;color:#e0e0e0;max-width:780px;margin:0 auto;padding:24px">
<div style="background:linear-gradient(135deg,#0f172a,#1e293b);padding:24px;
  border-radius:12px;margin-bottom:24px;border:1px solid #334155">
  <h1 style="margin:0 0 6px;font-size:22px;color:#f1f5f9">📈 FinTel Intelligence Digest</h1>
  <div style="font-size:13px;color:#94a3b8">{tickers} &nbsp;·&nbsp; {date_str}</div>
  <div style="margin-top:12px;font-size:13px">
    <span style="background:rgba(239,68,68,.2);color:#ef4444;padding:3px 10px;
      border-radius:20px;margin-right:8px">⚡ {len(high)} High</span>
    <span style="background:rgba(249,115,22,.2);color:#f97316;padding:3px 10px;
      border-radius:20px;margin-right:8px">◉ {len(medium)} Medium</span>
    <span style="background:rgba(34,197,94,.2);color:#22c55e;padding:3px 10px;
      border-radius:20px">○ {len(low)} Low</span>
  </div>
</div>
{section("⚡ High Priority",  "#ef4444", high)}
{section("◉ Medium Priority", "#f97316", medium)}
{section("○ Low Priority",    "#22c55e", low)}
<div style="margin-top:32px;font-size:11px;color:#444;text-align:center">
  FinTel · OpenAI GPT-4o + LangGraph · Not financial advice
</div>
</body></html>"""

    def _card_html(self, e: dict) -> str:
        color      = PRIORITY_COLORS.get(e.get("importance","Low"), "#22c55e")
        icon       = EVENT_ICONS.get(e.get("event_type","other"), "📌")
        sent_emoji = SENTIMENT_EMOJI.get(e.get("sentiment","neutral"), "◆")
        ticker     = e.get("ticker","")
        title      = e.get("representative_headline","") or e.get("tldr","")[:80]
        bullets    = "".join(
            f"<li style='margin:4px 0;color:#ccc'>{b}</li>"
            for b in e.get("key_facts", [])
        )
        urls  = [u for u in e.get("source_urls",[]) if u][:3]
        refs  = " ".join(
            f'<a href="{u}" style="color:#60a5fa;font-size:11px;margin-right:8px">source ↗</a>'
            for u in urls
        )
        flags = e.get("uncertainty_flags", [])
        flag_html = (
            f'<div style="background:#422;padding:6px 10px;border-radius:4px;'
            f'font-size:12px;color:#fbbf24;margin-top:8px">⚠ {"; ".join(flags)}</div>'
            if flags else ""
        )
        score = e.get("importance_score", 0)
        return f"""
<div style="border:1px solid #333;border-left:3px solid {color};border-radius:8px;
  padding:16px;margin:10px 0;background:#1a1a1a">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px">
    <strong style="color:#f0f0f0;font-size:14px">{icon} {title}</strong>
    <span style="color:{color};font-size:12px;font-weight:700;white-space:nowrap;
      margin-left:12px">{e.get('importance','')} ({score:.2f})</span>
  </div>
  <div style="font-size:12px;color:#666;margin-bottom:8px">
    {ticker} · {(e.get('event_type') or '').replace('_',' ').title()}
    · {e.get('article_count',0)} articles
    · {sent_emoji} {e.get('sentiment','neutral')}
  </div>
  <p style="color:#ddd;font-size:13px;margin:0 0 8px 0">{e.get('tldr','')}</p>
  <ul style="margin:0 0 10px 16px;font-size:13px;padding:0">{bullets}</ul>
  <div style="background:#0f2a1a;border:1px solid #1a4a2a;border-radius:6px;
    padding:10px;font-size:13px;color:#86efac">
    <strong>💼 Investment Perspective</strong><br>{e.get('impact','')}
  </div>
  {flag_html}
  <div style="margin-top:8px">{refs}</div>
</div>"""

    def _render_text(
        self,
        tickers: str,
        date_str: str,
        high: list[dict],
        medium: list[dict],
        low: list[dict],
    ) -> str:
        lines = [f"FinTel Digest — {tickers} — {date_str}", ""]
        for label, events in [("HIGH", high), ("MEDIUM", medium), ("LOW", low)]:
            for e in events:
                title = e.get("representative_headline","") or e.get("tldr","")[:80]
                lines += [f"[{label}] {title}", e.get("tldr",""), ""]
        return "\n".join(lines)


# ── LangGraph node wrapper ─────────────────────────────────────────────────────
def notification_agent(state: PipelineState) -> PipelineState:
    agent = NotificationAgent({})
    return agent.run(state)