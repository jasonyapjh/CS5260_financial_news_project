"""
JSON-based data storage for Streamlit application
No SQL database required - all data stored in JSON files
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

# Data directory
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# JSON file paths
WATCHLIST_FILE = DATA_DIR / "watchlist.json"
DIGESTS_FILE = DATA_DIR / "digests.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

def _load_json(filepath: Path, default: Any = None) -> Any:
    """Load JSON file, return default if not found"""
    if filepath.exists():
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return default if default is not None else {}
    return default if default is not None else {}

def _save_json(filepath: Path, data: Any):
    """Save data to JSON file"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)

def init_db():
    """Initialize JSON data files"""
    # Create empty files if they don't exist
    if not WATCHLIST_FILE.exists():
        _save_json(WATCHLIST_FILE, {})
    
    if not DIGESTS_FILE.exists():
        _save_json(DIGESTS_FILE, [])
    
    if not SETTINGS_FILE.exists():
        _save_json(SETTINGS_FILE, {})

def add_ticker(user_id: int, ticker: str) -> bool:
    """Add ticker to user's watchlist"""
    watchlist = _load_json(WATCHLIST_FILE, {})
    user_key = str(user_id)
    
    if user_key not in watchlist:
        watchlist[user_key] = []
    
    ticker = ticker.upper()
    
    # Check if already exists
    if ticker in watchlist[user_key]:
        return False
    
    watchlist[user_key].append(ticker)
    _save_json(WATCHLIST_FILE, watchlist)
    return True

def remove_ticker(user_id: int, ticker: str) -> bool:
    """Remove ticker from user's watchlist"""
    watchlist = _load_json(WATCHLIST_FILE, {})
    user_key = str(user_id)
    
    if user_key not in watchlist:
        return False
    
    ticker = ticker.upper()
    
    if ticker not in watchlist[user_key]:
        return False
    
    watchlist[user_key].remove(ticker)
    _save_json(WATCHLIST_FILE, watchlist)
    return True

def get_user_watchlist(user_id: int) -> List[str]:
    """Get user's stock ticker watchlist"""
    watchlist = _load_json(WATCHLIST_FILE, {})
    user_key = str(user_id)
    return watchlist.get(user_key, [])

def save_digest(user_id: int, digest_data: Dict[str, Any]) -> int:
    """Save digest to JSON file and return digest ID"""
    digests = _load_json(DIGESTS_FILE, [])
    
    # Generate digest ID
    digest_id = len(digests) + 1
    
    # Create digest record
    digest_record = {
        "id": digest_id,
        "user_id": user_id,
        "subject": digest_data.get("subject", ""),
        "html_digest": digest_data.get("html_digest", ""),
        "plain_text_digest": digest_data.get("plain_text_digest", ""),
        "tickers": digest_data.get("tickers", []),
        "event_counts": digest_data.get("event_counts", {}),
        "events": digest_data.get("events", []),
        "created_at": datetime.now().isoformat(),
        "execution_time": digest_data.get("execution_time", 0),
        "agent_timings": digest_data.get("agent_timings", {}),
    }
    
    digests.append(digest_record)
    _save_json(DIGESTS_FILE, digests)
    
    return digest_id

def get_digest_history(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    """Get user's digest history"""
    digests = _load_json(DIGESTS_FILE, [])
    
    # Filter by user and sort by creation date (newest first)
    user_digests = [d for d in digests if d.get("user_id") == user_id]
    user_digests.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return user_digests[:limit]

def get_digest_detail(digest_id: int) -> Dict[str, Any]:
    """Get full digest with events"""
    digests = _load_json(DIGESTS_FILE, [])
    
    for digest in digests:
        if digest.get("id") == digest_id:
            return digest
    
    return None

def get_llm_config(user_id: int) -> Dict[str, str]:
    """Get user's LLM configuration"""
    settings = _load_json(SETTINGS_FILE, {})
    user_key = str(user_id)
    
    if user_key in settings:
        return settings[user_key]
    
    return {"provider": "openai", "api_key": ""}

def save_llm_config(user_id: int, provider: str, api_key: str):
    """Save user's LLM configuration"""
    settings = _load_json(SETTINGS_FILE, {})
    user_key = str(user_id)
    
    settings[user_key] = {
        "provider": provider,
        "api_key": api_key,
        "updated_at": datetime.now().isoformat()
    }
    
    _save_json(SETTINGS_FILE, settings)

def delete_digest(digest_id: int) -> bool:
    """Delete digest from JSON file"""
    digests = _load_json(DIGESTS_FILE, [])
    
    # Find and remove digest
    for i, digest in enumerate(digests):
        if digest.get("id") == digest_id:
            digests.pop(i)
            _save_json(DIGESTS_FILE, digests)
            return True
    
    return False

def get_all_data() -> Dict[str, Any]:
    """Get all data (for debugging or export)"""
    return {
        "watchlist": _load_json(WATCHLIST_FILE, {}),
        "digests": _load_json(DIGESTS_FILE, []),
        "settings": _load_json(SETTINGS_FILE, {}),
    }

def export_data_to_json(filepath: str):
    """Export all data to a single JSON file"""
    all_data = get_all_data()
    with open(filepath, 'w') as f:
        json.dump(all_data, f, indent=2, default=str)

def clear_all_data():
    """Clear all data (use with caution)"""
    _save_json(WATCHLIST_FILE, {})
    _save_json(DIGESTS_FILE, [])
    _save_json(SETTINGS_FILE, {})
