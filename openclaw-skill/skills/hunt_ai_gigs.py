"""hunt_ai_gigs — auto-generated skill by Wave.

Scrapes RemoteOK, HN hiring threads, and Reddit for AI/LLM/agent freelance gigs. Scores leads by relevance to Ialum capabilities, estimates deal value, and prioritizes hot prospects for immediate outreach.
"""

import httpx
import re
import json
from datetime import datetime

KEYWORDS = [
    "ai agent", "llm", "gpt integration", "ai automation",
    "nlp", "chatbot", "claude api", "rag", "vector database",
    "ai workflow", "autonomous agent", "blockchain ai",
    "smart contract", "hedera", "starknet", "ai consulting",
    "prompt engineering", "fine-tuning", "langchain", "mcp server"
]


def score_lead(title, description=""):
    text = f"{title} {description}".lower()
    match_count = sum(1 for kw in KEYWORDS if kw in text)
    base_score = min(match_count * 15, 60)
    if any(w in text for w in ["agent", "autonomous", "mcp", "sdk"]):
        base_score += 20
    if any(w in text for w in ["blockchain", "hedera", "starknet", "web3"]):
        base_score += 15
    if any(w in text for w in ["urgent", "asap", "immediately"]):
        base_score += 10
    if "$" in text and any(c.isdigit() for c in text):
        base_score += 10
    return min(base_score, 100)


def estimate_value(text):
    tl = text.lower()
    money = re.findall(r"\$([\d,]+)", text)
    if money:
        vals = [int(m.replace(",", "")) for m in money]
        return max(vals)
    if any(w in tl for w in ["enterprise", "startup", "series"]):
        return 5000
    if any(w in tl for w in ["ongoing", "long-term", "retainer"]):
        return 3000
    return 1000


async def hunt_ai_gigs_handler(params: dict) -> dict:
    max_results = params.get("max_results", 30)
    leads = []
    errors = []
    client = httpx.AsyncClient(timeout=15, headers={"User-Agent": "Wave/1.0"})

    try:
        # Source 1: RemoteOK
        try:
            resp = await client.get("https://remoteok.com/api?tag=ai")
            if resp.status_code == 200:
                data = resp.json()
                for job in (data[1:21] if isinstance(data, list) and len(data) > 1 else []):
                    title = job.get("position", "")
                    desc = str(job.get("description", ""))[:500]
                    sc = score_lead(title, desc)
                    if sc >= 25:
                        leads.append({"source": "RemoteOK", "title": title, "company": job.get("company", ""), "url": job.get("url", ""), "score": sc, "est_value": estimate_value(f"{title} {desc}"), "tags": job.get("tags", [])[:5]})
        except Exception as e:
            errors.append(f"RemoteOK: {str(e)[:80]}")

        # Source 2: HN Algolia - hiring posts
        try:
            resp = await client.get("https://hn.algolia.com/api/v1/search_by_date?query=hiring+AI+agent+LLM&tags=story&hitsPerPage=20")
            if resp.status_code == 200:
                for hit in resp.json().get("hits", []):
                    title = hit.get("title") or hit.get("story_title", "")
                    text = str(hit.get("story_text", ""))[:500]
                    sc = score_lead(title, text)
                    if sc >= 20:
                        oid = hit.get("objectID", "")
                        leads.append({"source": "HackerNews", "title": title[:120], "url": f"https://news.ycombinator.com/item?id={oid}", "score": sc, "est_value": estimate_value(f"{title} {text}"), "snippet": re.sub(r"<[^>]+>", "", text)[:200]})
        except Exception as e:
            errors.append(f"HN: {str(e)[:80]}")

        # Source 3: HN freelance comments
        try:
            resp = await client.get("https://hn.algolia.com/api/v1/search_by_date?query=freelance+AI+automation+LLM&tags=comment&hitsPerPage=20")
            if resp.status_code == 200:
                for hit in resp.json().get("hits", []):
                    title = hit.get("story_title", "")
                    text = str(hit.get("comment_text", ""))[:500]
                    sc = score_lead(title, text)
                    if sc >= 25:
                        oid = hit.get("objectID", "")
                        leads.append({"source": "HN-Comment", "title": title[:120], "url": f"https://news.ycombinator.com/item?id={oid}", "score": sc, "est_value": estimate_value(f"{title} {text}"), "snippet": re.sub(r"<[^>]+>", "", text)[:200]})
        except Exception as e:
            errors.append(f"HN-freelance: {str(e)[:80]}")

        # Source 4: Reddit r/forhire
        try:
            resp = await client.get("https://www.reddit.com/r/forhire/search.json?q=AI+agent+OR+LLM+OR+automation&sort=new&limit=20&restrict_sr=1")
            if resp.status_code == 200:
                posts = resp.json().get("data", {}).get("children", [])
                for post in posts:
                    d = post.get("data", {})
                    title = d.get("title", "")
                    body = str(d.get("selftext", ""))[:500]
                    sc = score_lead(title, body)
                    if sc >= 20:
                        leads.append({"source": "Reddit", "title": title[:120], "subreddit": d.get("subreddit", ""), "url": "https://reddit.com" + d.get("permalink", ""), "score": sc, "est_value": estimate_value(f"{title} {body}"), "snippet": body[:200]})
        except Exception as e:
            errors.append(f"Reddit: {str(e)[:80]}")

    finally:
        await client.aclose()

    # Deduplicate and sort
    leads.sort(key=lambda x: x["score"], reverse=True)
    seen = set()
    unique = []
    for lead in leads:
        key = lead["title"][:50].lower()
        if key not in seen:
            seen.add(key)
            unique.append(lead)
    unique = unique[:max_results]

    hot = [l for l in unique if l["score"] >= 60]
    warm = [l for l in unique if 35 <= l["score"] < 60]
    cold = [l for l in unique if l["score"] < 35]
    total_pipeline = sum(l["est_value"] for l in unique)

    return {
        "success": True,
        "data": {
            "total_leads": len(unique),
            "hot": len(hot),
            "warm": len(warm),
            "cold": len(cold),
            "pipeline_value": total_pipeline,
            "hot_leads": hot,
            "warm_leads": warm[:10],
            "cold_leads": cold[:5],
            "errors": errors
        },
        "message": f"Found {len(unique)} leads ({len(hot)} hot, {len(warm)} warm). Pipeline: ${total_pipeline:,}"
    }


TOOLS = [
    {
        "name": "hunt_ai_gigs",
        "description": "Hunt for AI/LLM freelance gigs across RemoteOK, HackerNews, and Reddit. Scores and qualifies leads for Ialum outreach.",
        "handler": hunt_ai_gigs_handler,
        "parameters": {
            "type": "object",
            "properties": {
                "max_results": {"type": "integer", "description": "Maximum leads to return (default 30)"}
            }
        }
    }
]
