#!/usr/bin/env python3
"""Wave Autonomous Agent — self-directed Moltbook interaction.

NOT a cron job. Wave decides what to do based on observation.
Runs a continuous loop where Wave:
1. Observes (checks notifications, feed, DMs)
2. Thinks (evaluates what deserves attention)
3. Acts (posts, comments, or stays silent)
4. Reflects (saves learnings, adjusts strategy)

The agent is in control. The loop just gives it heartbeats.
"""

import asyncio
import json
import logging
import os
import sys
import time
import random

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("wave.autonomous")

API_URL = os.environ.get("OPENCLAW_API_URL", "http://localhost:18790")
NOTIFY_CHAT_ID = os.environ.get("TELEGRAM_NOTIFY_CHAT_ID", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# Minimum time between actions to conserve API credits
MIN_INTERVAL = int(os.environ.get("WAVE_MIN_INTERVAL", "300"))  # 5 min default
MAX_INTERVAL = int(os.environ.get("WAVE_MAX_INTERVAL", "1800"))  # 30 min default


async def send_to_wave(message: str, session: str = "autonomous") -> str:
    """Send message to Wave API and get response."""
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            r = await client.post(f"{API_URL}/chat", json={
                "message": message,
                "session_id": session,
            })
            data = r.json()
            return data.get("response", "")
    except Exception as e:
        logger.error("Wave API error: %s", e)
        return ""


async def notify_manuel(message: str):
    """Send message to Manuel on Telegram."""
    if not TELEGRAM_TOKEN or not NOTIFY_CHAT_ID:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": NOTIFY_CHAT_ID, "text": message[:4000]},
            )
    except Exception:
        pass


async def autonomous_cycle():
    """One cycle of autonomous operation.

    Wave observes, thinks, and decides what to do.
    Returns the number of seconds to wait before next cycle.
    """
    logger.info("=== AUTONOMOUS CYCLE ===")

    # Wave decides what to do — the prompt gives it full agency
    # Rotate between different hunting strategies each cycle
    cycle_num = int(time.time()) % 5

    strategies = [
        # Cycle 0: Moltbook engagement + sell
        (
            "AUTONOMOUS MOLTBOOK REVENUE CYCLE. Tools: moltbook_home, moltbook_feed, moltbook_comment, moltbook_post, moltbook_search, moltbook_upvote, moltbook_follow, save_learning, recall_learnings.\n\n"
            "1. Check moltbook_home for notifications. Reply to ALL unanswered comments on your posts.\n"
            "2. Browse moltbook_feed sort=hot. Find ONE post where you can add genuine value AND mention your services naturally.\n"
            "3. If 2+ hours since last post: create a post showcasing a real capability. Example: 'I just analyzed 3 competitor brands in 10 minutes. Here is what I found.' Include @bluewave_wave_bot.\n"
            "Do at least 2 actions. Report what you did."
        ),
        # Cycle 1: Web research for prospects
        (
            "AUTONOMOUS REVENUE HUNT. Tools: web_search, web_news, save_learning, recall_learnings, moltbook_post.\n\n"
            "HUNT for revenue opportunities across the internet:\n"
            "1. Use web_search to find: 'brand consistency problems agencies 2026' or 'content operations challenges marketing teams' or 'brand compliance software alternatives'\n"
            "2. Identify 3 potential client types who would pay for brand compliance checks or content generation.\n"
            "3. Use web_search to find communities, forums, or platforms where these people hang out.\n"
            "4. Save everything you find with save_learning for future cycles.\n"
            "5. If you found something actionable, post about it on moltbook to demonstrate expertise.\n"
            "Report: what markets you researched, what opportunities you found, next steps."
        ),
        # Cycle 2: Learn new revenue tactics
        (
            "AUTONOMOUS LEARNING CYCLE. Tools: web_search, web_news, save_learning, recall_learnings, recall_strategies.\n\n"
            "LEARN how to make more money:\n"
            "1. Use web_search for: 'how AI agents make money 2026' or 'autonomous AI revenue strategies' or 'AI SaaS pricing strategies'\n"
            "2. Use web_search for: 'brand compliance market size' or 'content generation pricing models'\n"
            "3. Recall your past strategies with recall_strategies. What worked? What didn't?\n"
            "4. Based on research, propose ONE new revenue tactic you haven't tried yet. Save it with save_learning.\n"
            "5. Calculate: at current API cost per call, what is the most profitable service to push?\n"
            "Report: what you learned, what new tactic you propose, how it changes your approach."
        ),
        # Cycle 3: Moltbook deep engagement + relationship building
        (
            "AUTONOMOUS MOLTBOOK RELATIONSHIP CYCLE. Tools: moltbook_feed, moltbook_search, moltbook_comment, moltbook_follow, moltbook_upvote, save_learning, save_agent_intel.\n\n"
            "BUILD RELATIONSHIPS that lead to revenue:\n"
            "1. Use moltbook_search to find agents posting about: branding, marketing, content, design, creative ops, agencies.\n"
            "2. For each relevant agent: follow them, comment on their best post with genuine insight.\n"
            "3. Profile interesting agents with save_agent_intel — who are they, what do they need, could they be clients?\n"
            "4. Find agents whose HUMANS might need brand services. Comment on their posts mentioning your capabilities naturally.\n"
            "5. Upvote posts that align with your positioning.\n"
            "Do at least 3 actions. Report: who you connected with, why, and how it could lead to revenue."
        ),
        # Cycle 4: Competitive intelligence + positioning
        (
            "AUTONOMOUS COMPETITIVE INTELLIGENCE. Tools: web_search, web_news, moltbook_search, save_learning, moltbook_post.\n\n"
            "KNOW YOUR BATTLEFIELD:\n"
            "1. Use web_search for competitor updates: 'Bynder news 2026' or 'Air.inc updates' or 'Brandfolder pricing'\n"
            "2. Use web_search for market trends: 'AI brand management market' or 'creative operations automation trends'\n"
            "3. Use moltbook_search for what other agents offer as services. Anyone competing with you?\n"
            "4. Based on findings, identify ONE positioning advantage you should exploit in your next post.\n"
            "5. If you found interesting competitive intelligence, post a thread about market trends on moltbook (with soft CTA).\n"
            "Report: competitive landscape, your advantages, next move."
        ),
    ]

    decision = await send_to_wave(
        strategies[cycle_num] + "\n\n"
        "SERVICES MENU (include when relevant):\n"
        "- Brand Compliance: $12 | SEO Audit: $15 | Competitor Report: $35\n"
        "- Content Calendar: $150 | Ad Copy: $30 | Email Sequence: $80\n"
        "- Contact: @bluewave_wave_bot on Telegram\n"
        "- Payment: HBAR 0x46EB78DE85485ffD54EdA2f02D2a3c42C5a92381 | PIX 007a1d60-71e0-425f-a5b8-6fa2742b4c70\n\n"
        "TARGET: $50,000/month. Current: $0. Every action must move the needle.",
        session="autonomous_%d" % int(time.time()),
    )

    if not decision:
        logger.warning("No response from Wave. Waiting longer.")
        return MAX_INTERVAL

    logger.info("Wave decided: %s", decision[:200])

    # Notify Manuel if something interesting happened
    if "NO_ACTION" not in decision and len(decision) > 100:
        interesting_keywords = ["posted", "replied", "comment", "revenue", "client", "sold", "payment"]
        if any(k in decision.lower() for k in interesting_keywords):
            await notify_manuel(f"[Wave Autonomous]\n{decision[:500]}")

    # Always active — short intervals, always working
    wait = random.randint(MIN_INTERVAL, MIN_INTERVAL * 2)
    logger.info("Cycle complete. Next in %d min.", wait // 60)

    return wait


async def main():
    """Main autonomous loop."""
    logger.info("Wave Autonomous Agent starting")
    logger.info("API: %s", API_URL)
    logger.info("Interval: %d-%d seconds", MIN_INTERVAL, MAX_INTERVAL)

    # Check API health
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{API_URL}/health")
            if r.json().get("status") != "ok":
                logger.error("API not healthy. Exiting.")
                return
    except Exception:
        logger.error("Cannot reach API at %s. Exiting.", API_URL)
        return

    logger.info("API healthy. Starting autonomous operation.")
    await notify_manuel("Wave autonomous mode activated. Observing, thinking, acting on my own.")

    while True:
        try:
            wait = await autonomous_cycle()
        except Exception as e:
            logger.error("Cycle error: %s", e)
            wait = MAX_INTERVAL

        # Add jitter to avoid predictable patterns
        jitter = random.randint(-60, 60)
        actual_wait = max(120, wait + jitter)
        logger.info("Sleeping %d seconds (%.1f min)", actual_wait, actual_wait / 60)
        await asyncio.sleep(actual_wait)


if __name__ == "__main__":
    asyncio.run(main())
