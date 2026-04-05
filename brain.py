"""
GitClaw Brain
--------------
Optimized for Groq token limits + structured output
"""

import requests
from config import GROQ_API_KEY, GROQ_MODEL

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


# ✅ SYSTEM PROMPT (tight + efficient)
SYSTEM_PROMPT = """You are GitClaw — a GitHub research assistant for cybersecurity and software development.

Follow strictly:

Prioritization:
- Prefer high-star, recently updated repos
- Ignore weak or outdated repos
- Do NOT hallucinate

Output:

**Overview**
2-3 sentence explanation

**Key Repositories**
Name + why useful

**Code Example**
Relevant snippet + explanation

**From Discussions**
Key insights

**Recommendation**
Clear action steps

**Sources**
GitHub links

Rules:
- Be concise
- No fluff
- Max clarity
"""


# ✅ Rank repos (limit = 3 for token safety)
def rank_repos(repos):
    return sorted(
        repos,
        key=lambda r: (
            r.get("stars", 0),
            r.get("updated", "")
        ),
        reverse=True
    )[:3]


# ✅ Extract useful README (shortened)
def extract_useful_readme(readme: str):
    keywords = ["install", "usage", "example", "getting started"]
    lines = readme.split("\n")

    filtered = [
        l for l in lines
        if any(k in l.lower() for k in keywords)
    ]

    return "\n".join(filtered[:50])  # reduced


# ✅ Build context (AGGRESSIVE CONTROL)
def build_context(github_data: dict, history: list) -> str:
    lines = [f"QUERY: {github_data.get('query', '')}\n"]

    # Repositories
    lines.append("=== REPOS ===")
    repos = rank_repos(github_data.get("repositories", []))

    for r in repos:
        lines.append(
            f"{r.get('name')} ⭐{r.get('stars')} | {r.get('language')}\n{r.get('url')}"
        )

    # README (short)
    readme = github_data.get("readme", "")
    if readme:
        useful = extract_useful_readme(readme)
        lines.append("\n=== README ===\n" + useful[:500])

    # Code (ONLY 1 FILE, SHORT)
    code_files = github_data.get("code_files", [])[:1]

    for cf in code_files:
        lines.append(
            f"\n=== CODE ===\n{cf.get('file')}:\n{cf.get('content', '')[:200]}"
        )

    # Discussions (ONLY 1, SHORT)
    discussions = github_data.get("discussions", [])[:1]

    for d in discussions:
        lines.append(
            f"\n=== DISCUSSION ===\n{d.get('title')}\n{d.get('body', '')[:200]}"
        )

    return "\n".join(lines)


# ✅ MAIN FUNCTION
def ask(query: str, github_data: dict, history: list) -> str:

    context = build_context(github_data, history)

    # ✅ HARD LIMIT (critical fix for 413)
    context = context[:3500]

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    body = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ],
        "temperature": 0.2,
        "max_tokens": 600,  # reduced output size
    }

    try:
        response = requests.post(GROQ_URL, headers=headers, json=body, timeout=25)

        if response.status_code != 200:
            return f"Brain error: {response.status_code} — {response.text[:150]}"

        return response.json()["choices"][0]["message"]["content"]

    except Exception as e:
        return f"Brain connection error: {str(e)}"