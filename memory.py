"""
GitClaw Memory System
----------------------
Stores per-user search history and context in a local JSON file.
Each user gets their own memory slot keyed by Telegram user ID.
"""

import json
import os
from datetime import datetime
from config import MEMORY_FILE, MAX_HISTORY


def _load() -> dict:
    """Load full memory file."""
    if not os.path.exists(MEMORY_FILE):
        return {}
    with open(MEMORY_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def _save(data: dict):
    """Save full memory file."""
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_user(user_id: int) -> dict:
    """Get a user's memory. Creates default if not exists."""
    data = _load()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {
            "requests_today": 0,
            "last_request_date": "",
            "history": [],
            "last_answer": "",
        }
        _save(data)
    return data[uid]


def save_search(user_id: int, query: str, answer: str):
    """Save a search query + answer to user history."""
    data = _load()
    uid = str(user_id)
    today = datetime.now().strftime("%Y-%m-%d")

    if uid not in data:
        data[uid] = {
            "requests_today": 0,
            "last_request_date": "",
            "history": [],
            "last_answer": "",
        }

    # Reset daily counter if new day
    if data[uid]["last_request_date"] != today:
        data[uid]["requests_today"] = 0
        data[uid]["last_request_date"] = today

    # Increment request count
    data[uid]["requests_today"] += 1
    data[uid]["last_answer"] = answer

    # Add to history (keep last MAX_HISTORY)
    data[uid]["history"].append({
        "date": today,
        "query": query,
        "answer": answer[:500],  # Trim for storage
    })
    data[uid]["history"] = data[uid]["history"][-MAX_HISTORY:]

    _save(data)


def get_request_count(user_id: int) -> int:
    """Get how many requests user made today."""
    data = _load()
    uid = str(user_id)
    today = datetime.now().strftime("%Y-%m-%d")

    if uid not in data:
        return 0
    if data[uid].get("last_request_date") != today:
        return 0
    return data[uid].get("requests_today", 0)


def get_history(user_id: int) -> list:
    """Get user's past search history."""
    user = get_user(user_id)
    return user.get("history", [])


def get_last_answer(user_id: int) -> str:
    """Get user's last answer (for /save command)."""
    user = get_user(user_id)
    return user.get("last_answer", "")


def save_to_vault(user_id: int, query: str, answer: str):
    """Save a result to the user's personal vault."""
    data = _load()
    uid = str(user_id)

    if uid not in data:
        data[uid] = {"history": [], "vault": [], "last_answer": ""}

    if "vault" not in data[uid]:
        data[uid]["vault"] = []

    data[uid]["vault"].append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "query": query,
        "answer": answer[:1000],
    })

    _save(data)


def get_vault(user_id: int) -> list:
    """Get user's saved vault entries."""
    user = get_user(user_id)
    return user.get("vault", [])
