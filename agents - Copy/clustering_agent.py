"""Agent 4: Event Clustering — groups articles into distinct financial events."""
from utils.llm import call_openai, extract_json
from utils.state import PipelineState
import json
PROMPT = """You are a financial analyst. Group these news articles into distinct event clusters.
Each cluster = one underlying business/financial event.

Event types: earnings, guidance, M&A, product_launch, regulation, litigation,
executive_change, partnership, analyst_rating, macro, market_trend, other

Return ONLY a JSON array:
[{{
  "cluster_id": "c1",
  "event_type": "earnings",
  "event_title": "Descriptive title of the event",
  "tickers_affected": ["AAPL"],
  "article_indices": [0, 3, 7]
}}]

Articles:
{articles_text}"""


def clustering_agent(state: PipelineState) -> PipelineState:
    state["current_step"] = 4
    state["step_logs"].append("[Agent 4] Clustering articles into events...")

    articles = state.get("clean_articles", [])
    if not articles:
        state["event_clusters"] = []
        state["step_logs"].append("[Agent 4] ✓ No articles to cluster")
        return state

    text = "\n".join(
        f"[{i}] [{a.get('ticker','')}] {a['headline']} | {a.get('snippet','')[:120]}"
        for i, a in enumerate(articles)
    )

    try:
        resp = call_openai(PROMPT.format(articles_text=text), state["openai_key"])
        raw = extract_json(resp)
    except Exception as e:
        raw = [{"cluster_id": f"c{i}", "event_type": "other", "event_title": a["headline"],
                "tickers_affected": [a.get("ticker","")], "article_indices": [i]}
               for i, a in enumerate(articles)]

    clusters = []
    for c in raw:
        linked = [articles[i] for i in c.get("article_indices", []) if 0 <= i < len(articles)]
        clusters.append({**c, "articles": linked})

    output_path = "agent_4_output.json"
    with open(output_path, "w") as f:
        json.dump(clusters, f, indent=4)

    # with open("agent_4_output.json", "r") as f:
    #     clusters = json.load(f)
    state["event_clusters"] = clusters
    state["step_logs"].append(f"[Agent 4] ✓ Formed {len(clusters)} event clusters")
    return state
