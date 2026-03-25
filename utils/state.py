from typing import TypedDict, Optional


class PipelineState(TypedDict):
    # Inputs
    watchlist: list[str]
    openai_key: str
    #newsapi_key: str

    # Agent 1 output
    query_bundles: list[dict]

    # Progress tracking
    current_step: int
    step_logs: list[str]
    error: Optional[str]