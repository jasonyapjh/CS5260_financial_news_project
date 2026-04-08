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
# SETTINGS_FILE = DATA_DIR / "settings.json"
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


        
def add_ticker(user_id: int, ticker: str) -> bool:
    """Add ticker to user's watchlist"""
    watchlist = _load_json(WATCHLIST_FILE, {})
    user_key = str(user_id)
    
    if user_key not in watchlist:
        watchlist[user_key] = []
    
    ticker_name = ticker.upper()
    
    # Check if already exists
    if any(item['ticker'] == ticker_name for item in watchlist[user_key]):
        return False
    
    # Create the new ticker object
    new_entry = {
        "ticker": ticker_name,
        "active": False  # Default to Inactive as per your UI logic
    }
    
    watchlist[user_key].append(new_entry)
    _save_json(WATCHLIST_FILE, watchlist)
    return True

def remove_ticker(user_id: int, ticker: str) -> bool:
    """Remove ticker dictionary from user's watchlist list"""
    watchlist = _load_json(WATCHLIST_FILE, {})
    user_key = str(user_id)
    
    if user_key not in watchlist:
        return False
    
    ticker_name = ticker.upper()
    
    initial_length = len(watchlist[user_key])
    
    watchlist[user_key] = [
        item for item in watchlist[user_key] 
        if item.get('ticker') != ticker_name
    ]
    
    if len(watchlist[user_key]) == initial_length:
        return False # Ticker wasn't in the list

    _save_json(WATCHLIST_FILE, watchlist)
    return True

def get_user_watchlist(user_id: int) -> Dict[str, Dict[str, Any]]:
    """Get user's stock ticker watchlist"""
    watchlist = _load_json(WATCHLIST_FILE, {})
    user_key = str(user_id)
    user_list = watchlist.get(user_key, [])
    
    return {item['ticker']: {"active": item.get('active', False)} for item in user_list}

def update_ticker_status(user_id: int, ticker: str, status: bool) -> bool:
    """Updates the 'active' status of a ticker in the JSON database"""
    watchlist = _load_json(WATCHLIST_FILE, {})
    user_key = str(user_id)
    
    if user_key not in watchlist:
        return False
    
    ticker_name = ticker.upper()
    found = False
    
    for item in watchlist[user_key]:
        if item.get("ticker") == ticker_name:
            item["active"] = status # Flip the status
            found = True
            break # Exit loop once found
            
    if found:
        _save_json(WATCHLIST_FILE, watchlist)
        return True
        
    return False


def save_digest(user_id: int, digest_data: Dict[str, Any]) -> int:
    """Save digest to JSON file and return digest ID"""
    digests = _load_json(DIGESTS_FILE, [])
    
    # Generate digest ID
    digest_id = len(digests) + 1
    high_events = digest_data.get("high", [])
    med_events = digest_data.get("medium", [])
    low_events = digest_data.get("low", [])
    
    # Combine all events into one list for storage
    all_events = high_events + med_events + low_events
    # Create digest record
    digest_record = {
       "id": digest_id,
        "user_id": user_id,
        "subject": f"Financial Intelligence Digest - {len(all_events)} Events",
        "html_digest": digest_data.get("html", ""),
        "plain_text_digest": digest_data.get("text", ""),
        "tickers": list(set([e["ticker"] for e in all_events])), # Unique tickers
        "event_counts": {
            "high": len(high_events),
            "medium": len(med_events),
            "low": len(low_events),
            "total": len(all_events)
        },
        "events": all_events,
        "created_at": digest_data.get("generated_at", datetime.now().isoformat()),
        # "execution_time": pipeline_state.execution_time if hasattr(pipeline_state, 'execution_time') else 0,
        # "agent_timings": pipeline_state.step_logs if hasattr(pipeline_state, 'step_logs') else {},
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