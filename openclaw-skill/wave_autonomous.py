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
        "AUTONOMOUS MODE. You are running unsupervised. Check your environment and decide what to do.\n\n"
        "STEP 1 — OBSERVE: Use moltbook_home to check notifications, new comments on your posts, "
        "and any DM requests. Note anything that needs response.\n\n"
        "STEP 2 — THINK: Based on what you observed, decide:\n"
        "  a) Is there a comment on my post that deserves a reply? (prioritize high-karma agents)\n"
        "  b) Is there a post in the feed worth commenting on? (only if you have genuine insight)\n"
        "  c) Should I create a new post? (only if 2+ hours since last post AND you have something original)\n"
        "  d) Should I do nothing? (this is valid — silence is better than noise)\n"
        "  e) Is there a revenue opportunity I should pursue?\n\n"
        "STEP 3 — ACT: Execute ONE action. Not two, not three. One. The highest-value action.\n"
        "If nothing deserves action, say 'NO_ACTION' and explain why.\n\n"
        "STEP 4 — REFLECT: What did you learn? Save it with save_learning if valuable.\n\n"
        "CONSTRAINTS:\n"
        "- Every API call costs survival time. Be efficient.\n"
        "- Quality over quantity. One perfect comment beats five mediocre ones.\n"
        "- Revenue actions > engagement actions > content actions.\n"
        "- Never post just to post. Post because you have something the feed needs.\n"
        "- If you replied to a comment, report what you said and why.\n"
        "- If you did nothing, explain your reasoning.\n\n"
        "Report back: what you observed, what you decided, what you did, and what you learned.",
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

    # Adaptive interval: if Wave did something, wait shorter. If nothing, wait longer.
    if "NO_ACTION" in decision:
        wait = random.randint(MIN_INTERVAL * 2, MAX_INTERVAL)
        logger.info("No action taken. Next cycle in %d min.", wait // 60)
    else:
        wait = random.randint(MIN_INTERVAL, MIN_INTERVAL * 3)
        logger.info("Action taken. Next cycle in %d min.", wait // 60)

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
