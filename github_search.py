"""
GitClaw GitHub Search Engine (Upgraded)
--------------------------------------
Optimized for quality, relevance, and low-noise AI input
"""

import base64
import requests
from config import (
    GITHUB_TOKEN,
    MAX_REPOS,
    MAX_CODE_FILES,
    MAX_DISCUSSIONS,
    README_CHAR_LIMIT,
    CODE_CHAR_LIMIT,
)

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


# ✅ MULTI QUERY BUILDER
def build_search_queries(user_query: str):
    base = user_query.lower()

    return [
        f"{base} implementation stars:>50",
        f"{base} example stars:>30",
        f"{base} best practices security stars:>50",
        f"{base} pushed:>2022 stars:>20",
    ]


# ✅ FILTER LOW QUALITY REPOS
def filter_repos(repos):
    return [
        r for r in repos
        if r.get("stars", 0) > 20
        and r.get("description")
    ]


# ✅ REMOVE DUPLICATES
def dedupe_repos(repos):
    seen = set()
    unique = []

    for r in repos:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique.append(r)

    return unique


# ✅ SEARCH REPOSITORIES
def search_repositories(query: str) -> list[dict]:
    try:
        r = requests.get(
            "https://api.github.com/search/repositories",
            headers=HEADERS,
            params={
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": MAX_REPOS,
            },
            timeout=10,
        )

        if r.status_code != 200:
            return []

        return [
            {
                "type": "repository",
                "name": i["full_name"],
                "description": i.get("description", "No description"),
                "url": i["html_url"],
                "stars": i["stargazers_count"],
                "language": i.get("language", "Unknown"),
                "topics": i.get("topics", []),
                "updated": i.get("updated_at", "")[:10],
            }
            for i in r.json().get("items", [])
        ]

    except Exception:
        return []


# ✅ FETCH README
def fetch_readme(repo_full_name: str) -> str:
    try:
        r = requests.get(
            f"https://api.github.com/repos/{repo_full_name}/readme",
            headers=HEADERS,
            timeout=10,
        )

        if r.status_code != 200:
            return ""

        content = r.json().get("content", "")
        decoded = base64.b64decode(content).decode("utf-8", errors="ignore")

        return decoded[:README_CHAR_LIMIT]

    except Exception:
        return ""


# ✅ SEARCH CODE (IMPROVED)
def search_code(query: str) -> list[dict]:
    try:
        r = requests.get(
            "https://api.github.com/search/code",
            headers=HEADERS,
            params={
                "q": f"{query} language:python",
                "per_page": MAX_CODE_FILES,
            },
            timeout=10,
        )

        if r.status_code != 200:
            return []

        return [
            {
                "type": "code",
                "file": i["name"],
                "path": i["path"],
                "repo": i["repository"]["full_name"],
                "url": i["html_url"],
                "api_url": i.get("url", ""),
            }
            for i in r.json().get("items", [])
        ]

    except Exception:
        return []


# ✅ FETCH CODE CONTENT
def fetch_file_content(api_url: str) -> str:
    try:
        r = requests.get(api_url, headers=HEADERS, timeout=10)

        if r.status_code != 200:
            return ""

        content = r.json().get("content", "")
        decoded = base64.b64decode(content).decode("utf-8", errors="ignore")

        return decoded[:CODE_CHAR_LIMIT]

    except Exception:
        return ""


# ✅ SEARCH DISCUSSIONS
def search_discussions(query: str) -> list[dict]:
    gql = """
    query($q: String!) {
      search(query: $q, type: DISCUSSION, first: 5) {
        nodes {
          ... on Discussion {
            title
            url
            body
            repository { nameWithOwner }
            comments(first: 2) {
              nodes { body }
            }
          }
        }
      }
    }
    """

    try:
        r = requests.post(
            "https://api.github.com/graphql",
            headers=HEADERS,
            json={"query": gql, "variables": {"q": query}},
            timeout=10,
        )

        if r.status_code != 200:
            return []

        nodes = r.json().get("data", {}).get("search", {}).get("nodes", [])

        results = []

        for node in nodes[:MAX_DISCUSSIONS]:
            comments = node.get("comments", {}).get("nodes", [])

            results.append({
                "type": "discussion",
                "title": node.get("title", ""),
                "url": node.get("url", ""),
                "repo": node.get("repository", {}).get("nameWithOwner", ""),
                "body": (node.get("body", "") or "")[:300],
                "top_comment": (comments[0].get("body", "")[:200] if comments else ""),
            })

        return results

    except Exception:
        return []


# ✅ MAIN PIPELINE
def run_full_search(query: str) -> dict:

    # Multi-query repo search
    queries = build_search_queries(query)

    repos = []
    for q in queries:
        repos.extend(search_repositories(q))

    repos = filter_repos(repos)
    repos = dedupe_repos(repos)
    repos = repos[:MAX_REPOS]  # final limit

    # README
    readme = ""
    if repos:
        readme = fetch_readme(repos[0]["name"])

    # Code search
    code_files = search_code(query)

    enriched_code = []
    for cf in code_files[:1]:  # limit to 1 file
        if cf.get("api_url"):
            content = fetch_file_content(cf["api_url"])
            if content:
                enriched_code.append({**cf, "content": content})

    # Discussions
    discussions = search_discussions(query)

    return {
        "query": query,
        "repositories": repos,
        "readme": readme,
        "top_repo": repos[0]["name"] if repos else "",
        "code_files": enriched_code,
        "discussions": discussions,
    }