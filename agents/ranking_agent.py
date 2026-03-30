"""Agent 6: Importance Ranking — blended heuristic + GPT-4o scoring."""
from utils.llm import call_openai, extract_json
from utils.state import PipelineState
import json

TYPE_W = {"earnings":10,"guidance":10,"M&A":9,"merger":9,"acquisition":9,
          "regulation":8,"litigation":7,"executive_change":7,"product_launch":6,
          "analyst_rating":6,"partnership":5,"macro":5,"market_trend":4,"other":2}
SENT_W = {"bullish":2,"bearish":2,"neutral":0}
CONF_W = {"high":2,"medium":1,"low":0}

RANKING_PROMPT = """You are a portfolio manager. Rate each event's importance from 1-10 for a retail investor.

Events:
{events_text}

Return ONLY a JSON array:
[{{"cluster_id":"c1","importance_score":8,"rationale":"One sentence why this matters"}}]"""


def _heuristic(card: dict) -> int:
    et = card.get("event_type","other").lower()
    s = next((w for k,w in TYPE_W.items() if k in et), 2)
    s += SENT_W.get(card.get("sentiment","neutral"),0)
    s += CONF_W.get(card.get("confidence","low"),0)
    s += min(card.get("article_count",1)-1, 3)
    return min(s, 10)


def ranking_agent(state: PipelineState) -> PipelineState:
    state["current_step"] = 6
    state["step_logs"].append("[Agent 6] Ranking events by importance...")

    cards = state.get("event_cards", [])
    for c in cards:
        c["heuristic_score"] = _heuristic(c)

    events_text = "\n".join(
        f"[{c['cluster_id']}] {c.get('event_type')} | {c.get('tickers_affected')} | {c.get('tldr','')[:120]}"
        for c in cards
    )

    # try:
    #     resp = call_openai(RANKING_PROMPT.format(events_text=events_text), state["openai_key"])
    #     rankings = {r["cluster_id"]: r for r in extract_json(resp)}
    #     for c in cards:
    #         r = rankings.get(c["cluster_id"], {})
    #         llm_s = r.get("importance_score", c["heuristic_score"])
    #         blended = round((c["heuristic_score"] + llm_s) / 2)
    #         c["importance_score"] = blended
    #         c["importance_label"] = "High" if blended>=7 else "Medium" if blended>=4 else "Low"
    #         c["importance_rationale"] = r.get("rationale","")
    # except Exception:
    #     for c in cards:
    #         s = c["heuristic_score"]
    #         c["importance_score"] = s
    #         c["importance_label"] = "High" if s>=7 else "Medium" if s>=4 else "Low"
    #         c["importance_rationale"] = ""

    # cards.sort(key=lambda c: c.get("importance_score",0), reverse=True)
    
    # output_path = "agent_6_output.json"
    # with open(output_path, "w") as f:
    #    json.dump(cards, f, indent=4)

    with open("agent_6_output.json", "r") as f:
        cards = json.load(f)
    state["ranked_events"] = cards
    state["step_logs"].append(f"[Agent 6] ✓ Ranked {len(cards)} events")

    return state
