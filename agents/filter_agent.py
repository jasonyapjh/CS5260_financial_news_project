"""Agent 3: Noise Filtering & Deduplication."""
import hashlib
from utils.llm import call_openai, extract_json
from utils.state import PipelineState
import json

DEDUP_PROMPT = """You are a financial news editor. Review these articles and return the indices of articles to KEEP.
Remove: near-duplicates (same story, different source), generic market roundups, clickbait, irrelevant content.
Keep: specific, material financial news with factual content.

Return ONLY a JSON array of 0-based indices to keep. Example: [0, 2, 5, 8]

Articles:
{articles_text}"""


def _heuristic(articles: list[dict]) -> list[dict]:
    seen, out = set(), []
    for a in articles:
        h = (a.get("headline") or "").strip()
        if len(h) < 15:
            continue
        key = hashlib.md5(h.lower().encode()).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        if not a.get("snippet") and not a.get("content_preview"):
            continue
        out.append(a)
    return out


def filter_agent(state: PipelineState) -> PipelineState:
    state["current_step"] = 3
    state["step_logs"].append("[Agent 3] Filtering and deduplicating articles...")

    articles = _heuristic(state.get("raw_articles", []))
    kept = []

    try:
        # Remove article without content
        filtered_articles = [
            article for article in state["raw_articles"]
            if article.title and len(article.title) > 10
        ]

        # Deduplication: group similar titles
        seen_titles = set()
        kept = []
        for article in filtered_articles:
            title_lower = article.title.lower()[:50]  # First 50 chars
            if title_lower not in seen_titles:
                seen_titles.add(title_lower)
                kept.append(article)

    except Exception as e:
        state["error"] = f"Agent 3 failed: {e}"
        state["query_bundles"] = []
        
    # for i in range(0, len(articles), 25):
    #     batch = articles[i:i+25]
    #     text = "\n".join(f"[{j}] {a['headline']} | {a['snippet'][:100]}" for j, a in enumerate(batch))
    #     try:
    #         resp = call_openai(DEDUP_PROMPT.format(articles_text=text), state["openai_key"])
    #         indices = extract_json(resp)
    #         kept.extend(batch[idx] for idx in indices if 0 <= idx < len(batch))
    #     except Exception:
    #         kept.extend(batch)

    output_path = "agent_3_output.json"
    with open(output_path, "w") as f:
        json.dump(articles, f, indent=4)
    
    # with open("agent_3_output.json", "r") as f:
    #     kept = json.load(f)

    
    state["clean_articles"] = kept
    state["clean_article_count"] = len(kept)
    state["step_logs"].append(f"[Agent 3] ✓ {len(kept)} articles after filtering")
    return state
