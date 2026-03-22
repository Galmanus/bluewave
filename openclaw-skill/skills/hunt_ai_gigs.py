"""hunt_ai_gigs — auto-generated skill by Wave.

Hunts for high-value AI and blockchain freelance/contract opportunities across RemoteOK, HackerNews Who Is Hiring, and Web3 job boards. Scores and ranks by relevance to Ialum capabilities.
"""

import httpx
import json
import re
from datetime import datetime

KEYWORDS_AI = ["ai agent", "llm", "claude", "gpt", "langchain", "autonomous agent", "chatbot", "nlp", "machine learning", "ml ops", "fine-tuning", "rag", "retrieval augmented", "vector database", "embedding", "prompt engineer"]
KEYWORDS_CHAIN = ["hedera", "hashgraph", "solidity", "smart contract", "web3", "defi", "blockchain", "token", "nft", "dao", "starknet"]
KEYWORDS_TOOLS = ["mcp", "model context protocol", "automation", "api integration", "scraping", "data pipeline"]
ALL_KW = KEYWORDS_AI + KEYWORDS_CHAIN + KEYWORDS_TOOLS


def score_job(text, salary_max=0, is_remote=False, is_contract=False):
    text_lower = text.lower()
    matches = [k for k in ALL_KW if k in text_lower]
    if not matches:
        return 0, []
    score = min(1.0, len(matches) * 0.15)
    if any(k in text_lower for k in KEYWORDS_AI):
        score += 0.2
    if any(k in text_lower for k in KEYWORDS_CHAIN):
        score += 0.15
    if salary_max and salary_max > 100000:
        score += 0.1
    if is_remote:
        score += 0.05
    if is_contract:
        score += 0.1
    return round(min(1.0, score), 2), matches


async def hunt_ai_gigs(params: dict) -> dict:
    """Hunt for AI/blockchain gigs across multiple job sources."""
    max_results = params.get("max_results", 20)
    min_score = params.get("min_score", 0.3)
    opps = []
    errors = []

    async with httpx.AsyncClient(timeout=25, headers={"User-Agent": "Wave/1.0"}) as client:
        # Source 1: RemoteOK
        try:
            resp = await client.get("https://remoteok.com/api")
            if resp.status_code == 200:
                jobs = resp.json()
                for job in jobs[1:]:  # first is metadata
                    title = job.get("position", "")
                    desc = job.get("description", "") or ""
                    tags = " ".join(job.get("tags", []))
                    combined = title + " " + desc + " " + tags
                    sal_max = job.get("salary_max", 0) or 0
                    sc, matches = score_job(combined, sal_max)
                    if sc >= min_score:
                        opps.append({"source": "RemoteOK", "title": title, "company": job.get("company", "?"), "url": job.get("url", ""), "apply_url": job.get("apply_url", ""), "salary": "%sk-%sk" % (str(job.get("salary_min", "?")), str(sal_max)) if sal_max else "unlisted", "tags": job.get("tags", [])[:5], "matched": matches, "score": sc, "date": str(job.get("date", ""))[:10]})
        except Exception as e:
            errors.append("RemoteOK: %s" % str(e)[:80])

        # Source 2: HN Who Is Hiring
        try:
            resp = await client.get("https://hacker-news.firebaseio.com/v0/user/whoishiring.json")
            if resp.status_code == 200:
                user = resp.json()
                for story_id in user.get("submitted", [])[:2]:
                    sr = await client.get("https://hacker-news.firebaseio.com/v0/item/%d.json" % story_id)
                    if sr.status_code == 200:
                        story = sr.json()
                        if "who is hiring" in (story.get("title", "") or "").lower():
                            for kid_id in (story.get("kids", []))[:50]:
                                try:
                                    cr = await client.get("https://hacker-news.firebaseio.com/v0/item/%d.json" % kid_id)
                                    if cr.status_code == 200:
                                        c = cr.json()
                                        raw = c.get("text", "") or ""
                                        clean = re.sub(r"<[^>]+>", " ", raw)
                                        is_remote = "remote" in clean.lower()
                                        is_contract = any(w in clean.lower() for w in ["contract", "freelance", "consulting"])
                                        sc, matches = score_job(clean, 0, is_remote, is_contract)
                                        if sc >= min_score and len(matches) >= 2:
                                            first_line = clean.split("\n")[0][:150]
                                            opps.append({"source": "HN", "title": first_line, "company": first_line.split("|")[0].strip()[:60] if "|" in first_line else "see post", "url": "https://news.ycombinator.com/item?id=%d" % kid_id, "matched": matches, "score": sc, "remote": is_remote, "contract": is_contract})
                                except Exception:
                                    pass
                            break
        except Exception as e:
            errors.append("HN: %s" % str(e)[:80])

    # Sort and trim
    opps.sort(key=lambda x: x.get("score", 0), reverse=True)
    opps = opps[:max_results]

    sources = {}
    for o in opps:
        s = o["source"]
        sources[s] = sources.get(s, 0) + 1

    msg_lines = ["**Found %d opportunities (min score %.1f):**\n" % (len(opps), min_score)]
    for i, o in enumerate(opps[:10], 1):
        msg_lines.append("%d. [%.2f] **%s** @ %s" % (i, o["score"], o.get("title", "?")[:80], o.get("company", "?")))
        msg_lines.append("   Keywords: %s" % ", ".join(o.get("matched", [])[:4]))
        if o.get("url"):
            msg_lines.append("   %s" % o["url"])

    if errors:
        msg_lines.append("\n**Errors:** %s" % "; ".join(errors))

    return {"success": True, "data": {"opportunities": opps, "sources": sources, "errors": errors}, "message": "\n".join(msg_lines)}


TOOLS = [
    {
        "name": "hunt_ai_gigs",
        "description": "Hunt for AI/blockchain freelance and contract opportunities across RemoteOK and HN Who Is Hiring. Returns scored, ranked opportunities matching Ialum capabilities (AI agents, Hedera, MCP, automation).",
        "handler": hunt_ai_gigs,
        "parameters": {
            "type": "object",
            "properties": {
                "max_results": {"type": "integer", "description": "Max opportunities to return (default 20)"},
                "min_score": {"type": "number", "description": "Minimum relevance score 0-1 (default 0.3)"}
            }
        }
    }
]
