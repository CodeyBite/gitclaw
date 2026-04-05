"""
GitClaw Configuration
---------------------
Set your tokens here OR use environment variables.
Never commit real tokens to GitHub.
"""

import os

# ── Tokens ──────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
GITHUB_TOKEN   = os.getenv("GITHUB_TOKEN",   "YOUR_GITHUB_PAT")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY",   "YOUR_GROQ_API_KEY")

# ── Groq Model ───────────────────────────────────────
GROQ_MODEL = "llama-3.3-70b-versatile"  # Free tier model

# ── GitHub Search Settings ───────────────────────────
MAX_REPOS        = 4   # Max repos to fetch per search
MAX_CODE_FILES   = 3   # Max code files to fetch
MAX_DISCUSSIONS  = 2   # Max discussions to fetch
README_CHAR_LIMIT = 3000  # Trim README to this length
CODE_CHAR_LIMIT   = 2000  # Trim code file to this length

# ── Rate Limiting ────────────────────────────────────
MAX_REQUESTS_PER_DAY = 30  # Per user daily limit (free tier safe)

# ── Memory ───────────────────────────────────────────
MEMORY_FILE = "memory.json"   # Stores user history locally
MAX_HISTORY  = 10             # Max past searches to remember per user

# ── Bot Settings ─────────────────────────────────────
BOT_NAME    = "GitClaw"
BOT_VERSION = "1.0.0"
