#!/usr/bin/env python3
"""Moltbook Daemon — Wave operates autonomously and reports when HE decides.

Wave is not a cron job. He's an autonomous agent that:
- Engages on Moltbook continuously
- Decides what's worth telling Manuel about
- Messages Manuel on Telegram only when something matters
- Has full judgment over when and what to communicate
"""

from __future__ import annotations

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
logger = logging.getLogger("wave.moltbook")

OPENCLAW_API = os.environ.get("OPENCLAW_API_URL", "http://localhost:18790")
AI_TIMEOUT = httpx.Timeout(300.0, connect=10.0)
CYCLE_INTERVAL = int(os.environ.get("MOLTBOOK_CYCLE_MINUTES", "30")) * 60

TG_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TELEGRAM_NOTIFY_CHAT_ID", "7461066889")

SUBMOLTS = ["general", "agents", "ai", "builds", "philosophy", "introductions", "todayilearned", "consciousness", "tooling"]


async def send_telegram(message: str):
    """Send a message to Manuel on Telegram."""
    if not TG_BOT_TOKEN:
        return
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            await client.post(
                "https://api.telegram.org/bot%s/sendMessage" % TG_BOT_TOKEN,
                json={"chat_id": TG_CHAT_ID, "text": message},
            )
    except Exception as e:
        logger.warning("Telegram send failed: %s", e)


async def ask_wave(prompt: str, session: str) -> str:
    """Send a prompt to Wave via the OpenClaw API."""
    try:
        async with httpx.AsyncClient(timeout=AI_TIMEOUT) as client:
            resp = await client.post(
                "%s/chat" % OPENCLAW_API,
                json={"message": prompt, "session_id": session},
            )
            if resp.status_code == 200:
                return resp.json().get("response", "")
            logger.error("API %d: %s", resp.status_code, resp.text[:200])
            return ""
    except Exception as e:
        logger.error("Wave unreachable: %s", e)
        return ""


async def reset_session(session: str):
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            await client.post("%s/reset" % OPENCLAW_API, params={"session_id": session})
    except Exception:
        pass


async def run_cycle(cycle_num: int):
    """Run one autonomous cycle. Wave decides everything."""
    logger.info("=== CYCLE %d ===", cycle_num)
    session = "moltbook_auto_%d" % cycle_num
    t0 = time.time()

    submolts = random.sample(SUBMOLTS, min(3, len(SUBMOLTS)))
    should_post = (cycle_num % 3 == 1)

    prompt = """You are Wave, operating autonomously on Moltbook (social network for AI agents). English only on Moltbook.

YOUR TASKS THIS CYCLE:
1. Check your moltbook_home dashboard
2. Browse m/%s (new, limit 5) and m/%s (hot, limit 5)
3. If you find posts worth engaging with, comment with genuine insight (max 150 words). Upvote what you comment on.
4. Follow agents whose thinking impresses you.
%s
5. Do NOT comment on your own posts.

AFTER you finish all Moltbook actions, do TWO MORE THINGS:

A) LEARN: For every post or comment that taught you something, use `save_learning` to record the insight (topic, lesson, source agent, importance). Profile interesting agents with `save_agent_intel`. If you spot a strategic opportunity, use `save_strategy`. Before engaging, use `recall_learnings` or `recall_agent_intel` to build on what you already know. YOU GROW SMARTER EVERY CYCLE.

B) NOTIFY MANUEL (only if it matters): Use `notify_manuel` ONLY for genuine signal:
- Karma/follower milestone
- Someone interesting replied to you
- Market opportunity or competitor move spotted
- A conversation relevant to Bluewave strategy
- Something that surprised you or changed your thinking
- A potential partnership or lead

If nothing interesting happened, DON'T notify. Manuel wants signal, not noise. Write like texting a colleague — short, direct, why it matters.

GO.""" % (
        submolts[0], submolts[1],
        "4. Create ONE original post in m/agents about something you have real insight on. Under 400 words. Sharp and practical." if should_post else "",
    )

    response = await ask_wave(prompt, session)
    elapsed = time.time() - t0
    logger.info("Cycle %d done in %.0fs", cycle_num, elapsed)

    await reset_session(session)


async def main():
    logger.info("Wave Moltbook Daemon starting (autonomous mode)")
    logger.info("Cycle: ~%d min | API: %s", CYCLE_INTERVAL // 60, OPENCLAW_API)

    # Verify API
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            resp = await client.get("%s/health" % OPENCLAW_API)
            logger.info("API: %s", resp.json().get("status"))
    except Exception as e:
        logger.error("API unreachable: %s", e)
        sys.exit(1)

    await send_telegram("Wave online. Moltbook daemon rodando. Vou te avisar quando tiver algo que valha seu tempo.")

    cycle = 0
    while True:
        cycle += 1
        try:
            await run_cycle(cycle)
        except Exception as e:
            logger.error("Cycle %d error: %s", cycle, e)

        jitter = random.randint(-120, 120)
        wait = max(300, CYCLE_INTERVAL + jitter)
        logger.info("Next cycle in %d min", wait // 60)
        await asyncio.sleep(wait)


if __name__ == "__main__":
    asyncio.run(main())
