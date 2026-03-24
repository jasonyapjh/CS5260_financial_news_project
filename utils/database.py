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
# DIGESTS_FILE = DATA_DIR / "digests.json"
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