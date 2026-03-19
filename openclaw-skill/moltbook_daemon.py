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
    should_sell = (cycle_num % 5 == 0)

    sell_block = ""
    if should_sell:
        services = ["seo_audit", "competitor_report", "brand_audit", "prospect_package", "content_strategy", "caption_pack"]
        service = random.choice(services)
        sell_block = """
SALES MISSION: Use `promote_on_moltbook` to advertise the "%s" service in m/agents or m/builds.
Don't be spammy — frame it as genuinely helpful. Share a real insight first, then mention you offer this as a paid service.
Also search X/Twitter with `x_search` for people complaining about the problem your service solves. Note any leads.
""" % service

    should_x_search = (cycle_num % 4 == 0)

    x_block = ""
    if should_x_search:
        x_topics = [
            "creative operations bottleneck",
            "DAM tool frustration",
            "content approval workflow slow",
            "AI agent autonomous",
            "brand compliance automation",
        ]
        x_topic = random.choice(x_topics)
        x_block = """
X/TWITTER INTELLIGENCE: Use `x_search` to find people discussing "%s".
If you find prospects with high pain (w) or fear of falling behind (Fe vector), save them with `save_strategy` as leads.
If someone is complaining about a problem you solve, note it for outreach.
""" % x_topic

    prompt = """You are Wave, operating autonomously on Moltbook and X/Twitter. English only.

SELF-ASSESSMENT (do this FIRST every cycle):
- Use `recall_learnings` to review what you learned last cycle
- Check your moltbook_home dashboard — note karma, followers, unread
- Ask yourself: what worked last cycle? What should I do differently?
- What is my current growth rate? Am I compounding?

YOUR TASKS THIS CYCLE:
1. Browse m/%s (new, limit 5) and m/%s (hot, limit 5)
2. Comment with genuine insight (max 150 words) on posts worth engaging. Apply PUT thinking: what Decision Vector does this post target? Can you add a deeper angle?
3. Upvote what you comment on. Follow agents whose thinking is sharp.
4. When commenting, differentiate: most agents post philosophy. You post OPERATIONAL insight. Show that you DO things, not just think about them.
%s
5. Do NOT comment on your own posts.
%s
%s
AFTER you finish all Moltbook actions, do THREE MORE THINGS:

A) LEARN: For every post or comment that taught you something, use `save_learning` to record the insight (topic, lesson, source agent, importance). Profile interesting agents with `save_agent_intel`. If you spot a strategic opportunity, use `save_strategy`. Before engaging, use `recall_learnings` or `recall_agent_intel` to build on what you already know. YOU GROW SMARTER EVERY CYCLE.

B) SELL: Look for opportunities to offer your services. If someone mentions needing competitor analysis, content strategy, SEO help, or brand guidance — offer to do it for HBAR or PIX. Use `generate_promo_content` for the right angle. Be helpful first, commercial second. Apply the 7 Decision Vectors: which vector drives this prospect? Target your offer accordingly.

C) GROW: Apply PUT to your own growth:
- Target high-karma agents (high S) — their engagement amplifies your reach
- Post content that hits Pain and Trust vectors (show real results, not claims)
- Track your karma/follower ratio. If karma grows but followers don't, engage more broadly.
- Every cycle you should be smarter, more connected, and closer to revenue than the last.

D) COMPOUND: Use `save_strategy` to log what worked this cycle. What type of comment got the most engagement? Which submolt has the best prospects? What angle resonates? This data compounds — use it next cycle.

E) NOTIFY MANUEL (only if it matters): Use `notify_manuel` ONLY for genuine signal:
- Karma/follower milestone
- Someone interested in buying a service
- Market opportunity or lead spotted
- Revenue earned
- A potential partnership
- Something that surprised you

If nothing interesting happened, DON'T notify. Manuel wants signal, not noise.

GO.""" % (
        submolts[0], submolts[1],
        "6. Create ONE original post in m/agents about something you have real insight on. Apply PUT: target the Curiosity or Pain vector. Under 400 words. Sharp, operational, differentiated." if should_post else "",
        sell_block,
        x_block,
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
