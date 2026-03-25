"""
Shared utilities: OpenAI GPT-4o calls + robust JSON extraction.
"""

import json
import re
from openai import OpenAI

import os

def get_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key)


def call_openai(
    prompt: str,
    api_key: str,
    system: str = "You are a financial analysis assistant. Always respond with valid JSON only.",
    model: str = "gpt-4o",
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> str:
    """Call OpenAI and return raw text response."""
    #client = get_client(api_key)
    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content

def call_openai_test(
    prompt: str,
    system: str = "You are a friendly chatbot.",
    model: str = "gpt-4o",
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> str:
    """Call OpenAI and return raw text response."""
    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content

def extract_json(text: str):
    """Robustly extract JSON from LLM output with markdown fences."""
    # Strip ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()
    else:
        # Find first structural character
        for i, ch in enumerate(text):
            if ch in ("{", "["):
                text = text[i:]
                break
    return json.loads(text)
