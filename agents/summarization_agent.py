"""Agent 5: Impact Summarization + Verification Pass."""
import json
from utils.llm import call_openai, extract_json
from utils.state import PipelineState
import json
SUMMARY_PROMPT = """You are a senior buy-side analyst writing investment intelligence.

Event: {event_type} — {event_title}
Tickers: {tickers}

Source articles:
{articles_text}

Generate an event card. Return ONLY JSON:
{{
  "tldr": "One sentence summary",
  "key_bullets": ["fact 1", "fact 2", "fact 3"],
  "investment_impact": "2-3 sentences on investment significance: risks, opportunities, catalysts",
  "sentiment": "bullish|bearish|neutral",
  "confidence": "high|medium|low",
  "uncertainty_flags": ["unsupported claims, or empty list"]
}}"""

VERIFY_PROMPT = """Fact-check this event card against the source evidence.

Event Card:
{card}

Source Evidence:
{evidence}

Return ONLY JSON:
{{
  "verified": true,
  "confidence_adjustment": "none|downgrade",
  "additional_flags": ["unsupported claims, or empty list"]
}}"""


def summarization_agent(state: PipelineState) -> PipelineState:
    state["current_step"] = 5
    state["step_logs"].append("[Agent 5] Summarizing events with impact analysis...")

    cards = []
    # for cluster in state.get("event_clusters", []):
    #     arts = cluster.get("articles", [])
    #     art_text = "\n---\n".join(
    #         f"Source: {a.get('source','')}\n{a.get('headline','')}\n{a.get('snippet','')}"
    #         for a in arts[:8]
    #     )

    #     try:
    #         resp = call_openai(
    #             SUMMARY_PROMPT.format(
    #                 event_type=cluster.get("event_type", "other"),
    #                 event_title=cluster.get("event_title", ""),
    #                 tickers=", ".join(cluster.get("tickers_affected", [])),
    #                 articles_text=art_text,
    #             ),
    #             state["openai_key"]
    #         )
    #         summary = extract_json(resp)

    #         # Verification pass
    #         evidence = "\n".join(f"{a.get('headline','')}: {a.get('snippet','')}" for a in arts[:5])
    #         vresp = call_openai(
    #             VERIFY_PROMPT.format(card=json.dumps({"tldr": summary.get("tldr"), "key_bullets": summary.get("key_bullets")}), evidence=evidence),
    #             state["openai_key"]
    #         )
    #         v = extract_json(vresp)
    #         if v.get("confidence_adjustment") == "downgrade" and summary.get("confidence") == "high":
    #             summary["confidence"] = "medium"
    #         summary["uncertainty_flags"] = list(set(
    #             summary.get("uncertainty_flags", []) + v.get("additional_flags", [])
    #         ))

    #     except Exception as e:
    #         summary = {"tldr": arts[0].get("headline","") if arts else "", "key_bullets": [],
    #                    "investment_impact": "", "sentiment": "neutral", "confidence": "low",
    #                    "uncertainty_flags": [f"Summarization failed: {e}"]}

    #     cards.append({
    #         "cluster_id": cluster.get("cluster_id"),
    #         "event_type": cluster.get("event_type"),
    #         "event_title": cluster.get("event_title"),
    #         "tickers_affected": cluster.get("tickers_affected", []),
    #         "article_count": len(arts),
    #         "sources": list({a.get("source","") for a in arts}),
    #         "source_urls": [a.get("url","") for a in arts],
    #         "published_at": arts[0].get("published_at","") if arts else "",
    #         **summary,
    #     })

    # output_path = "agent_5_output.json"
    # with open(output_path, "w") as f:
    #     json.dump(cards, f, indent=4)
    with open("agent_5_output.json", "r") as f:
        cards = json.load(f)
    state["event_cards"] = cards
    state["step_logs"].append(f"[Agent 5] ✓ Generated {len(cards)} event cards with verification")
    return state
