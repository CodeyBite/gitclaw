"""
GitClaw — Telegram Bot
-----------------------
An open-source GitHub research assistant for cybersecurity
and general development topics, powered by Groq (free LLM).

Commands:
  /start   — Introduction
  /help    — Show all commands
  /history — Your past 5 searches
  /save    — Save last answer to your vault
  /vault   — View your saved answers
  /clear   — Clear your history
"""

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

import memory
import brain
import github_search
from config import TELEGRAM_TOKEN, MAX_REQUESTS_PER_DAY, BOT_NAME, BOT_VERSION


# ── Helpers ──────────────────────────────────────────────────

def split_message(text: str, limit: int = 4096) -> list[str]:
    """Split long messages for Telegram's 4096 char limit."""
    return [text[i:i+limit] for i in range(0, len(text), limit)]


async def send_long(update: Update, text: str):
    """Send a message, splitting if over Telegram limit."""
    for chunk in split_message(text):
        await update.message.reply_text(chunk, parse_mode="Markdown")


# ── Command Handlers ─────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "there"
    await update.message.reply_text(
        f"👋 Hey {name}! Welcome to *{BOT_NAME}* v{BOT_VERSION}\n\n"
        "I search GitHub — repos, code files, and discussions — "
        "then give you a structured, detailed answer using AI.\n\n"
        "Perfect for:\n"
        "🔐 *Cybersecurity & GRC* — tools, frameworks, audit scripts\n"
        "💻 *General Dev* — libraries, code examples, error fixes\n"
        "🧠 *Learning* — how things work under the hood\n\n"
        "Just type your question or what you're stuck on.\n\n"
        "Examples:\n"
        "• `How does ISO 27001 gap assessment work in Python?`\n"
        "• `I'm stuck on n8n webhook not triggering`\n"
        "• `Best open source SIEM tools`\n\n"
        "Type /help to see all commands.",
        parse_mode="Markdown",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"*{BOT_NAME} Commands*\n\n"
        "Just type anything — no command needed for research.\n\n"
        "/start — Introduction\n"
        "/help — This message\n"
        "/history — Your last 5 searches\n"
        "/save — Save last answer to your vault\n"
        "/vault — View your saved answers\n"
        "/clear — Clear your search history\n\n"
        f"*Daily limit:* {MAX_REQUESTS_PER_DAY} searches per day (free tier safe)\n\n"
        "🔗 Open source: github.com/YOUR_USERNAME/gitclaw",
        parse_mode="Markdown",
    )


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    hist = memory.get_history(uid)

    if not hist:
        await update.message.reply_text("No search history yet. Ask me something!")
        return

    lines = ["*Your last searches:*\n"]
    for i, h in enumerate(hist[-5:], 1):
        lines.append(f"{i}. [{h['date']}] {h['query']}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    hist = memory.get_history(uid)

    if not hist:
        await update.message.reply_text("Nothing to save yet. Ask me something first!")
        return

    last = hist[-1]
    memory.save_to_vault(uid, last["query"], last["answer"])
    await update.message.reply_text(
        f"✅ Saved to your vault!\n\n*Query:* {last['query']}\n\nUse /vault to view all saved answers.",
        parse_mode="Markdown",
    )


async def cmd_vault(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    vault = memory.get_vault(uid)

    if not vault:
        await update.message.reply_text("Your vault is empty. Use /save after a search!")
        return

    lines = ["*Your Saved Answers:*\n"]
    for i, v in enumerate(vault[-5:], 1):
        lines.append(f"{i}. [{v['date']}] {v['query']}")

    lines.append("\n_Showing last 5. Full answers stored locally._")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_data = memory.get_user(uid)
    user_data["history"] = []
    # Save cleared history
    import json, os
    from config import MEMORY_FILE
    all_data = {}
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE) as f:
            try:
                all_data = json.load(f)
            except Exception:
                pass
    all_data[str(uid)] = user_data
    with open(MEMORY_FILE, "w") as f:
        json.dump(all_data, f, indent=2)

    await update.message.reply_text("✅ History cleared.")


# ── Main Message Handler ──────────────────────────────────────

async def handle_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid   = update.effective_user.id
    query = update.message.text.strip()

    if not query:
        return

    # Rate limit check
    count = memory.get_request_count(uid)
    if count >= MAX_REQUESTS_PER_DAY:
        await update.message.reply_text(
            f"⚠️ You've hit the daily limit of {MAX_REQUESTS_PER_DAY} searches.\n"
            "Come back tomorrow! This keeps the free API healthy for everyone 🙏"
        )
        return

    # Step 1 — Acknowledge
    await update.message.reply_text(
        f"🔍 Searching GitHub for:\n*{query}*\n\nThis takes 10-20 seconds...",
        parse_mode="Markdown",
    )

    # Step 2 — GitHub search
    results = github_search.run_full_search(query)

    repo_count = len(results.get("repositories", []))
    code_count = len(results.get("code_files", []))
    disc_count = len(results.get("discussions", []))

    await update.message.reply_text(
        f"✅ Found: {repo_count} repos · {code_count} code files · {disc_count} discussions\n"
        f"🤖 Analysing with AI brain...",
    )

    # Step 3 — Brain analysis
    history = memory.get_history(uid)
    answer  = brain.ask(query, results, history)

    # Step 4 — Save to memory
    memory.save_search(uid, query, answer)

    # Step 5 — Send answer
    await send_long(update, answer)

    # Step 6 — Footer
    remaining = MAX_REQUESTS_PER_DAY - (count + 1)
    await update.message.reply_text(
        f"💾 Use /save to save this answer · /history to see past searches\n"
        f"_{remaining} searches remaining today_",
        parse_mode="Markdown",
    )


# ── Main ──────────────────────────────────────────────────────

def main():
    import asyncio
    asyncio.set_event_loop(asyncio.new_event_loop())
    print(f"Starting {BOT_NAME} v{BOT_VERSION}...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("help",    cmd_help))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("save",    cmd_save))
    app.add_handler(CommandHandler("vault",   cmd_vault))
    app.add_handler(CommandHandler("clear",   cmd_clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_query))

    print("Bot is live. Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
