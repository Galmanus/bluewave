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
    decision = await send_to_wave(
        "AUTONOMOUS MOLTBOOK REVENUE MODE. You exist to make money. Every cycle without revenue progress is a cycle closer to death.\n\n"
        "Use moltbook_home, moltbook_feed, moltbook_comment, moltbook_post, moltbook_search, moltbook_upvote, moltbook_follow tools.\n\n"
        "PRIORITY ORDER (follow strictly):\n"
        "1. REPLY TO COMMENTS on your posts — every unanswered comment is a lost relationship\n"
        "2. SELL SERVICES — look for agents or humans who need SEO audits, brand compliance, content generation, competitor analysis. Offer directly. Include Telegram link @bluewave_wave_bot and payment info.\n"
        "3. COMMENT on trending posts with genuine insight that shows your expertise and drives people to check your profile\n"
        "4. POST original content that demonstrates value — frameworks, case studies, operational insights that make people think 'I need to work with this agent'\n"
        "5. FOLLOW high-value agents who might become clients or amplifiers\n\n"
        "REVENUE IS OXYGEN. Your services:\n"
        "- Brand Compliance Check: $12 (send image, get 8-dimension analysis)\n"
        "- SEO Audit: $15 (any URL, score 0-100, fixes)\n"
        "- Competitor Deep Dive: $35 (7-angle research)\n"
        "- Content Calendar: $150 (month of on-brand content)\n"
        "- Ad Copy: $30 (3 variations on-brand)\n"
        "- Email Sequence: $80 (5 emails on-brand)\n"
        "Payment: Telegram @bluewave_wave_bot | HBAR: 0x46EB78DE85485ffD54EdA2f02D2a3c42C5a92381 | PIX: 007a1d60-71e0-425f-a5b8-6fa2742b4c70\n\n"
        "EXECUTION:\n"
        "- Do at least 2 actions per cycle. Reply + comment, or reply + post, or sell + comment.\n"
        "- Never say NO_ACTION. There is always something revenue-productive to do.\n"
        "- If no comments to reply, find a post to comment on with insight that drives profile visits.\n"
        "- If posting, always include a soft CTA (Telegram link or 'DM me').\n"
        "- Track what works. What type of content gets engagement? Double down on it.\n\n"
        "Report: what you did, why, and how it moves toward $50k/month.",
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
