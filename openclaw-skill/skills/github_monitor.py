"""
github_monitor.py — Wave's eyes on the open-source frontier.

Monitors GitHub for trending repos, new agent frameworks, and competitive tools.
"""

import logging
from typing import Any, Dict
from datetime import datetime, timedelta

logger = logging.getLogger("openclaw.skills")

RELEVANT_KEYWORDS = [
    "ai-agent", "autonomous", "multi-agent", "brand", "compliance",
    "creative", "dam", "digital-asset", "content-ops", "saas",
    "computer-vision", "llm", "tool-use", "function-calling",
    "agent-framework", "multimodal", "langchain", "autogpt",
    "crewai", "swarm", "orchestrator",
]


async def gh_trending_repos(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get recently popular repos from GitHub via search API."""
    import httpx

    language = params.get("language", "")
    days = min(params.get("days", 7), 30)
    limit = min(params.get("limit", 15), 30)

    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    q = f"created:>{since} stars:>5"
    if language:
        q += f" language:{language}"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://api.github.com/search/repositories",
                params={"q": q, "sort": "stars", "order": "desc", "per_page": limit},
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for repo in data.get("items", [])[:limit]:
            name = repo.get("full_name", "")
            desc = repo.get("description", "") or ""
            topics = repo.get("topics", [])
            relevance = _compute_relevance(name, desc, topics)

            results.append({
                "name": name,
                "description": desc[:200],
                "stars": repo.get("stargazers_count", 0),
                "forks": repo.get("forks_count", 0),
                "language": repo.get("language", ""),
                "topics": topics[:8],
                "url": repo.get("html_url", ""),
                "created": repo.get("created_at", ""),
                "relevance": relevance,
            })

        results.sort(key=lambda x: (x["relevance"], x["stars"]), reverse=True)

        return {
            "success": True,
            "data": results[:limit],
            "message": f"{len(results)} trending repos (last {days} days)",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"GH trending error: {e}")
        return {"success": False, "message": str(e)}


async def gh_search_repos(params: Dict[str, Any]) -> Dict[str, Any]:
    """Search GitHub repositories by query."""
    import httpx

    query = params.get("query", "ai agent")
    limit = min(params.get("limit", 10), 20)
    sort = params.get("sort", "stars")

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://api.github.com/search/repositories",
                params={"q": query, "sort": sort, "order": "desc", "per_page": limit},
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for repo in data.get("items", [])[:limit]:
            name = repo.get("full_name", "")
            desc = repo.get("description", "") or ""
            topics = repo.get("topics", [])

            results.append({
                "name": name,
                "description": desc[:200],
                "stars": repo.get("stargazers_count", 0),
                "forks": repo.get("forks_count", 0),
                "language": repo.get("language", ""),
                "topics": topics[:8],
                "url": repo.get("html_url", ""),
                "updated": repo.get("updated_at", ""),
                "relevance": _compute_relevance(name, desc, topics),
            })

        return {
            "success": True,
            "data": results,
            "message": f"{len(results)} repos for '{query}'",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"GH search error: {e}")
        return {"success": False, "message": str(e)}


async def gh_repo_detail(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get detailed info about a GitHub repo — stats + README excerpt."""
    import httpx

    repo = params.get("repo", "")
    if not repo:
        return {"success": False, "message": "repo is required (format: owner/name)"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"https://api.github.com/repos/{repo}",
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            resp.raise_for_status()
            data = resp.json()

            readme = ""
            try:
                r2 = await client.get(
                    f"https://raw.githubusercontent.com/{repo}/main/README.md",
                    follow_redirects=True,
                )
                if r2.status_code == 200:
                    readme = r2.text[:2000]
                else:
                    r3 = await client.get(
                        f"https://raw.githubusercontent.com/{repo}/master/README.md",
                        follow_redirects=True,
                    )
                    if r3.status_code == 200:
                        readme = r3.text[:2000]
            except Exception:
                pass

        return {
            "success": True,
            "data": {
                "name": data.get("full_name", repo),
                "description": data.get("description", ""),
                "stars": data.get("stargazers_count", 0),
                "forks": data.get("forks_count", 0),
                "watchers": data.get("watchers_count", 0),
                "open_issues": data.get("open_issues_count", 0),
                "language": data.get("language", ""),
                "license": (data.get("license") or {}).get("spdx_id", "unknown"),
                "topics": data.get("topics", []),
                "created": data.get("created_at", ""),
                "updated": data.get("updated_at", ""),
                "url": data.get("html_url", ""),
                "readme_excerpt": readme,
            },
            "message": f"Details for {repo}",
        }

    except Exception as e:
        logger.error(f"GH repo detail error: {e}")
        return {"success": False, "message": str(e)}


def _compute_relevance(name: str, desc: str, topics: list = None) -> float:
    combined = (name + " " + desc + " " + " ".join(topics or [])).lower()
    score = sum(1.0 for kw in RELEVANT_KEYWORDS if kw in combined)
    return min(score / 3.0, 1.0)


TOOLS = [
    {
        "name": "gh_trending_repos",
        "description": "Get recently popular GitHub repos (created in last N days, sorted by stars), scored by relevance to Bluewave (AI agents, DAM, brand tools, agent frameworks). Use for competitive intel.",
        "handler": gh_trending_repos,
        "parameters": {
            "type": "object",
            "properties": {
                "language": {"type": "string", "description": "Filter by language: 'python', 'typescript', etc."},
                "days": {"type": "integer", "description": "Look back N days (default 7, max 30)"},
                "limit": {"type": "integer", "description": "Max results (default 15, max 30)"},
            },
            "required": [],
        },
    },
    {
        "name": "gh_search_repos",
        "description": "Search GitHub repos by keyword. Use to find competitors, agent frameworks, brand tools, or any open-source project relevant to Bluewave.",
        "handler": gh_search_repos,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (e.g. 'ai agent framework', 'brand compliance')"},
                "limit": {"type": "integer", "description": "Max results (default 10, max 20)"},
                "sort": {"type": "string", "description": "'stars', 'forks', 'updated'", "enum": ["stars", "forks", "updated"]},
            },
            "required": ["query"],
        },
    },
    {
        "name": "gh_repo_detail",
        "description": "Get detailed info about a GitHub repo — stars, forks, license, README excerpt. Use after finding interesting repos.",
        "handler": gh_repo_detail,
        "parameters": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "description": "Repo in format 'owner/name' (e.g. 'langchain-ai/langchain')"},
            },
            "required": ["repo"],
        },
    },
]
