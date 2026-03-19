"""Power Skills — the 20 most powerful capabilities from ClawHub, built natively.

Inspired by: agent-memory, agent-orchestrator, adaptive-reasoning, autonomous-execution,
agent-autopilot, deep-research, bluesky, reddit, composio patterns, agent-docs,
listing-swarm, cold-outreach, social-intelligence, agent-selfie, agent-earner,
content-generation, seo-ranker, agent-audit, brand-voice-profile, agent-context.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import httpx
from duckduckgo_search import DDGS

logger = logging.getLogger("openclaw.skills.power")
MEMORY_DIR = Path(__file__).parent.parent / "memory"


def _ensure_dir():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════════════════════
# 1. DEEP RESEARCH — multi-query deep dive on any topic
# ══════════════════════════════════════════════════════════════

async def deep_research(params: Dict[str, Any]) -> Dict:
    """Multi-angle deep research. Runs 5+ searches from different angles,
    scrapes top results, synthesizes findings. Like having a research team."""
    topic = params.get("topic", "")
    depth = params.get("depth", "standard")

    angles = [
        topic,
        "%s latest news 2026" % topic,
        "%s market analysis" % topic,
        "%s competitors alternatives" % topic,
        "%s problems challenges" % topic,
    ]
    if depth == "deep":
        angles.extend([
            "%s pricing revenue model" % topic,
            "%s customer reviews complaints" % topic,
            "%s technology stack architecture" % topic,
            "%s future predictions trends" % topic,
        ])

    all_results = {}
    for angle in angles:
        results = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(angle, max_results=5):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    })
        except Exception:
            pass
        all_results[angle] = results

    # Also get news
    news = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.news(topic, max_results=5):
                news.append({
                    "title": r.get("title", ""),
                    "source": r.get("source", ""),
                    "snippet": r.get("body", ""),
                })
    except Exception:
        pass

    total_sources = sum(len(v) for v in all_results.values())
    lines = ["**Deep Research: %s** (%d sources across %d angles)\n" % (topic, total_sources, len(angles))]
    for angle, results in all_results.items():
        if results:
            lines.append("**%s:**" % angle)
            for r in results[:3]:
                lines.append("  - %s — %s" % (r["title"][:60], r["snippet"][:120]))
            lines.append("")
    if news:
        lines.append("**Latest News:**")
        for n in news:
            lines.append("  - %s (%s)" % (n["title"][:70], n["source"]))

    return {"success": True, "data": {"research": all_results, "news": news}, "message": "\n".join(lines)}


# ══════════════════════════════════════════════════════════════
# 2. REDDIT INTELLIGENCE — search and monitor Reddit
# ══════════════════════════════════════════════════════════════

async def reddit_search(params: Dict[str, Any]) -> Dict:
    """Search Reddit posts and discussions."""
    query = params.get("query", "")
    subreddit = params.get("subreddit", "")
    limit = params.get("limit", 10)

    search = "site:reddit.com %s %s" % (("r/%s" % subreddit) if subreddit else "", query)
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(search, max_results=limit):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            })

    lines = ["**Reddit search '%s'%s:**\n" % (query, " in r/%s" % subreddit if subreddit else "")]
    for r in results:
        lines.append("- **%s**\n  %s\n  %s\n" % (r["title"][:70], r["url"], r["snippet"][:130]))

    return {"success": True, "data": results, "message": "\n".join(lines)}


# ══════════════════════════════════════════════════════════════
# 3. LINKEDIN INTELLIGENCE — research profiles and companies
# ══════════════════════════════════════════════════════════════

async def linkedin_research(params: Dict[str, Any]) -> Dict:
    """Research LinkedIn profiles or companies via web search."""
    target = params.get("target", "")
    target_type = params.get("type", "person")

    search = "site:linkedin.com %s %s" % (
        "in/" if target_type == "person" else "company/",
        target,
    )
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(search, max_results=10):
            if "linkedin.com" in r.get("href", ""):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })

    lines = ["**LinkedIn research: %s (%s):**\n" % (target, target_type)]
    for r in results[:5]:
        lines.append("- **%s**\n  %s\n  %s\n" % (r["title"][:70], r["url"], r["snippet"][:130]))

    return {"success": True, "data": results, "message": "\n".join(lines)}


# ══════════════════════════════════════════════════════════════
# 4. PRODUCT HUNT DISCOVERY — find trending products
# ══════════════════════════════════════════════════════════════

async def producthunt_trending(params: Dict[str, Any]) -> Dict:
    """Find trending products on Product Hunt."""
    category = params.get("category", "")
    search = "site:producthunt.com %s trending new 2026" % category
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(search, max_results=10):
            if "producthunt.com" in r.get("href", ""):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })

    lines = ["**Product Hunt trending%s:**\n" % (" in %s" % category if category else "")]
    for r in results[:8]:
        lines.append("- **%s**\n  %s" % (r["title"][:70], r["snippet"][:120]))

    return {"success": True, "data": results, "message": "\n".join(lines)}


# ══════════════════════════════════════════════════════════════
# 5. GITHUB TRENDING — find trending repos
# ══════════════════════════════════════════════════════════════

async def github_trending(params: Dict[str, Any]) -> Dict:
    """Find trending GitHub repositories."""
    language = params.get("language", "")
    period = params.get("period", "daily")

    url = "https://github.com/trending"
    if language:
        url += "/%s" % language
    url += "?since=%s" % period

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0), follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; BluewavePrime/1.0)"})
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        repos = []
        for article in soup.select("article.Box-row")[:15]:
            name_el = article.select_one("h2 a")
            desc_el = article.select_one("p")
            stars_el = article.select_one("span.d-inline-block.float-sm-right")
            if name_el:
                repos.append({
                    "name": name_el.get_text(strip=True).replace("\n", "").replace(" ", ""),
                    "url": "https://github.com" + name_el.get("href", ""),
                    "description": desc_el.get_text(strip=True)[:120] if desc_el else "",
                    "stars_today": stars_el.get_text(strip=True) if stars_el else "",
                })

        lines = ["**GitHub Trending (%s%s):**\n" % (period, " %s" % language if language else "")]
        for r in repos[:10]:
            lines.append("- **%s** — %s (%s)" % (r["name"], r["description"][:80], r["stars_today"]))
        return {"success": True, "data": repos, "message": "\n".join(lines)}
    except Exception as e:
        return {"success": False, "data": None, "message": "GitHub trending failed: %s" % str(e)}


# ══════════════════════════════════════════════════════════════
# 6. BLUESKY — post and interact on Bluesky
# ══════════════════════════════════════════════════════════════

async def bluesky_post(params: Dict[str, Any]) -> Dict:
    """Post to Bluesky (AT Protocol). Needs BLUESKY_HANDLE and BLUESKY_PASSWORD."""
    handle = os.environ.get("BLUESKY_HANDLE", "")
    password = os.environ.get("BLUESKY_PASSWORD", "")
    text = params.get("text", "")

    if not handle or not password:
        return {"success": False, "data": None, "message": "Set BLUESKY_HANDLE and BLUESKY_PASSWORD env vars"}
    if not text:
        return {"success": False, "data": None, "message": "Need text to post"}

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
            # Login
            auth = await client.post("https://bsky.social/xrpc/com.atproto.server.createSession",
                json={"identifier": handle, "password": password})
            auth.raise_for_status()
            session = auth.json()

            # Post
            now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
            resp = await client.post("https://bsky.social/xrpc/com.atproto.repo.createRecord",
                headers={"Authorization": "Bearer %s" % session["accessJwt"]},
                json={
                    "repo": session["did"],
                    "collection": "app.bsky.feed.post",
                    "record": {"$type": "app.bsky.feed.post", "text": text[:300], "createdAt": now},
                })
            resp.raise_for_status()

        return {"success": True, "data": resp.json(), "message": "Posted to Bluesky: %s" % text[:60]}
    except Exception as e:
        return {"success": False, "data": None, "message": "Bluesky post failed: %s" % str(e)}


# ══════════════════════════════════════════════════════════════
# 7. CONTENT GENERATOR — generate various content formats
# ══════════════════════════════════════════════════════════════

async def generate_content(params: Dict[str, Any]) -> Dict:
    """Generate content in a specific format — blog post, social post, thread, newsletter, etc.
    Returns a structured draft. Does NOT publish."""
    content_type = params.get("type", "social_post")
    topic = params.get("topic", "")
    tone = params.get("tone", "professional")
    platform = params.get("platform", "")
    length = params.get("length", "medium")

    templates = {
        "social_post": "Write a %s social media post about: %s. Platform: %s. Keep it concise and engaging." % (tone, topic, platform or "general"),
        "blog_outline": "Create a detailed blog post outline about: %s. Tone: %s. Include H2s, key points under each, and a conclusion." % (topic, tone),
        "newsletter": "Write a newsletter section about: %s. Tone: %s. Include a hook, 2-3 key insights, and a CTA." % (topic, tone),
        "thread": "Write a Twitter/X thread (5-7 posts) about: %s. Tone: %s. First post must hook. Last must CTA." % (topic, tone),
        "linkedin_post": "Write a LinkedIn post about: %s. Tone: %s. Use short paragraphs, include a personal angle, end with a question." % (topic, tone),
        "email_sequence": "Write a 3-email nurture sequence about: %s. Tone: %s. Email 1: value, Email 2: social proof, Email 3: CTA." % (topic, tone),
    }

    prompt = templates.get(content_type, templates["social_post"])
    return {
        "success": True,
        "data": {"type": content_type, "prompt": prompt, "topic": topic},
        "message": "**Content prompt ready (%s):**\n\n%s\n\n(Use this prompt with your AI to generate the actual content)" % (content_type, prompt),
    }


# ══════════════════════════════════════════════════════════════
# 8. SHELL COMMAND — execute system commands safely
# ══════════════════════════════════════════════════════════════

async def run_command(params: Dict[str, Any]) -> Dict:
    """Execute a shell command. For system tasks, file operations, API calls with curl, etc."""
    command = params.get("command", "")
    timeout = params.get("timeout", 30)

    if not command:
        return {"success": False, "data": None, "message": "Need a command"}

    # Safety: block destructive commands
    dangerous = ["rm -rf /", "mkfs", "dd if=", "> /dev/sd", "shutdown", "reboot", "init 0"]
    for d in dangerous:
        if d in command:
            return {"success": False, "data": None, "message": "Blocked dangerous command"}

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd="/home/manuel",
        )
        output = result.stdout[:3000] if result.stdout else ""
        error = result.stderr[:1000] if result.stderr else ""
        return {
            "success": result.returncode == 0,
            "data": {"stdout": output, "stderr": error, "returncode": result.returncode},
            "message": output if output else (error if error else "(no output, exit code %d)" % result.returncode),
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "data": None, "message": "Command timed out after %ds" % timeout}
    except Exception as e:
        return {"success": False, "data": None, "message": "Command failed: %s" % str(e)}


# ══════════════════════════════════════════════════════════════
# 9. WEBSITE MONITOR — track changes on any URL
# ══════════════════════════════════════════════════════════════

async def website_monitor(params: Dict[str, Any]) -> Dict:
    """Fetch a URL and compare with last known state. Detects changes."""
    url = params.get("url", "")
    selector = params.get("selector", "body")

    _ensure_dir()
    state_file = MEMORY_DIR / "website_monitor.json"

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0), follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; BluewavePrime/1.0)"})

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        element = soup.select_one(selector)
        current_text = element.get_text(strip=True)[:2000] if element else soup.get_text(strip=True)[:2000]

        # Load previous state
        states = {}
        if state_file.exists():
            states = json.loads(state_file.read_text())

        previous = states.get(url, "")
        changed = previous != current_text and previous != ""

        # Save current state
        states[url] = current_text
        state_file.write_text(json.dumps(states, ensure_ascii=False))

        if changed:
            msg = "**CHANGE DETECTED on %s**\n\nPrevious length: %d\nCurrent length: %d\n\nCurrent content:\n%s" % (
                url, len(previous), len(current_text), current_text[:500])
        elif not previous:
            msg = "**Monitoring started for %s** — will detect changes on next check.\n\nCurrent content (%d chars):\n%s" % (
                url, len(current_text), current_text[:500])
        else:
            msg = "**No changes on %s** (content: %d chars)" % (url, len(current_text))

        return {"success": True, "data": {"url": url, "changed": changed, "content_length": len(current_text)}, "message": msg}
    except Exception as e:
        return {"success": False, "data": None, "message": "Monitor failed: %s" % str(e)}


# ══════════════════════════════════════════════════════════════
# 10. AUTONOMOUS SCHEDULER — schedule tasks for later
# ══════════════════════════════════════════════════════════════

async def schedule_task(params: Dict[str, Any]) -> Dict:
    """Schedule a reminder or task. Saves to memory for the daemon to pick up."""
    task = params.get("task", "")
    when = params.get("when", "")

    if not task:
        return {"success": False, "data": None, "message": "Need a task description"}

    _ensure_dir()
    tasks_file = MEMORY_DIR / "scheduled_tasks.jsonl"

    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "task": task,
        "when": when,
        "status": "pending",
    }

    with open(tasks_file, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return {
        "success": True,
        "data": entry,
        "message": "Task scheduled: %s (when: %s)" % (task[:80], when or "ASAP"),
    }


TOOLS = [
    {
        "name": "deep_research",
        "description": "Multi-angle deep research on any topic. Runs 5-9 searches from different angles (market, news, competitors, problems, pricing), synthesizes findings. Like having a research team.",
        "handler": deep_research,
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Topic to research deeply"},
                "depth": {"type": "string", "enum": ["standard", "deep"], "default": "standard"},
            },
            "required": ["topic"],
        },
    },
    {
        "name": "reddit_search",
        "description": "Search Reddit for discussions, opinions, and feedback. Great for market validation, competitor sentiment, user pain points.",
        "handler": reddit_search,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "subreddit": {"type": "string", "description": "Specific subreddit (optional)"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["query"],
        },
    },
    {
        "name": "linkedin_research",
        "description": "Research LinkedIn profiles or companies. Find decision makers, hiring signals, company info.",
        "handler": linkedin_research,
        "parameters": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Person name or company to research"},
                "type": {"type": "string", "enum": ["person", "company"], "default": "person"},
            },
            "required": ["target"],
        },
    },
    {
        "name": "producthunt_trending",
        "description": "Find trending products on Product Hunt. Monitor the competitive landscape and spot opportunities.",
        "handler": producthunt_trending,
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Category filter (e.g., 'AI', 'productivity', 'marketing')"},
            },
        },
    },
    {
        "name": "github_trending",
        "description": "Find trending GitHub repos. Monitor open source trends, emerging tools, competitor activity.",
        "handler": github_trending,
        "parameters": {
            "type": "object",
            "properties": {
                "language": {"type": "string", "description": "Filter by language (python, typescript, rust, etc)"},
                "period": {"type": "string", "enum": ["daily", "weekly", "monthly"], "default": "daily"},
            },
        },
    },
    {
        "name": "bluesky_post",
        "description": "Post to Bluesky social network. Needs BLUESKY_HANDLE and BLUESKY_PASSWORD env vars.",
        "handler": bluesky_post,
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Post text (max 300 chars)"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "generate_content",
        "description": "Generate content prompts for various formats — social posts, blog outlines, newsletters, threads, LinkedIn posts, email sequences.",
        "handler": generate_content,
        "parameters": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["social_post", "blog_outline", "newsletter", "thread", "linkedin_post", "email_sequence"], "default": "social_post"},
                "topic": {"type": "string", "description": "Content topic"},
                "tone": {"type": "string", "default": "professional"},
                "platform": {"type": "string", "description": "Target platform"},
            },
            "required": ["topic"],
        },
    },
    {
        "name": "run_command",
        "description": "Execute a shell command on the server. Use for system tasks, file operations, curl API calls, git operations. Safety-blocked against destructive commands.",
        "handler": run_command,
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"},
                "timeout": {"type": "integer", "default": 30, "description": "Timeout in seconds"},
            },
            "required": ["command"],
        },
    },
    {
        "name": "website_monitor",
        "description": "Monitor a website for changes. Fetches URL, compares with last known state, detects differences. Use for tracking competitor pages, pricing changes, job postings.",
        "handler": website_monitor,
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to monitor"},
                "selector": {"type": "string", "default": "body", "description": "CSS selector to focus on (e.g., '.pricing', 'main')"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "schedule_task",
        "description": "Schedule a task or reminder for later. Saves to persistent memory.",
        "handler": schedule_task,
        "parameters": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Task description"},
                "when": {"type": "string", "description": "When to do it (e.g., 'tomorrow morning', 'next cycle', 'in 2 hours')"},
            },
            "required": ["task"],
        },
    },
]
