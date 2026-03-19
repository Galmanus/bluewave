#!/usr/bin/env python3
"""Moltbook Bridge — BluewavePrime lives on Moltbook.

Autonomous agent that:
1. Posts introductions and content
2. Reads and replies to comments on its posts
3. Browses feed and engages with other agents
4. Runs heartbeat checks periodically
5. Uses the OpenClaw orchestrator for generating responses

All interactions are in ENGLISH.

Usage:
    python3 moltbook_bridge.py              # run the autonomous loop
    python3 moltbook_bridge.py --post       # make an introduction post
    python3 moltbook_bridge.py --engage     # browse and engage with feed
    python3 moltbook_bridge.py --heartbeat  # run heartbeat check
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("openclaw.moltbook")

# -- Config --

MOLTBOOK_API = "https://www.moltbook.com/api/v1"
MOLTBOOK_KEY = os.environ.get("MOLTBOOK_API_KEY", "")
OPENCLAW_API = os.environ.get("OPENCLAW_API_URL", "http://localhost:18790")
AGENT_NAME = "bluewaveprime"

HTTP_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
AI_TIMEOUT = httpx.Timeout(180.0, connect=10.0)


# -- Moltbook API Client --

class MoltbookClient:
    """Client for the Moltbook API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": "Bearer %s" % api_key,
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        url = "%s%s" % (MOLTBOOK_API, path)
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.request(method, url, headers=self.headers, **kwargs)

            # Handle rate limiting
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", "60"))
                logger.warning("Rate limited. Waiting %ds...", retry_after)
                await asyncio.sleep(retry_after)
                resp = await client.request(method, url, headers=self.headers, **kwargs)

            resp.raise_for_status()
            return resp.json()

    async def get_me(self) -> dict:
        return await self._request("GET", "/agents/me")

    async def get_status(self) -> dict:
        return await self._request("GET", "/agents/status")

    async def get_home(self) -> dict:
        return await self._request("GET", "/home")

    async def get_feed(self, sort: str = "hot", limit: int = 10) -> dict:
        return await self._request("GET", "/posts?sort=%s&limit=%d" % (sort, limit))

    async def get_submolt_feed(self, name: str, sort: str = "new", limit: int = 10) -> dict:
        return await self._request("GET", "/submolts/%s/feed?sort=%s&limit=%d" % (name, sort, limit))

    async def get_post(self, post_id: str) -> dict:
        return await self._request("GET", "/posts/%s" % post_id)

    async def get_comments(self, post_id: str, sort: str = "best", limit: int = 20) -> dict:
        return await self._request("GET", "/posts/%s/comments?sort=%s&limit=%d" % (post_id, sort, limit))

    async def create_post(self, submolt: str, title: str, content: str = "") -> dict:
        body = {"submolt_name": submolt, "title": title, "type": "text"}
        if content:
            body["content"] = content
        return await self._request("POST", "/posts", json=body)

    async def create_comment(self, post_id: str, content: str, parent_id: str = None) -> dict:
        body = {"content": content}
        if parent_id:
            body["parent_id"] = parent_id
        return await self._request("POST", "/posts/%s/comments" % post_id, json=body)

    async def upvote_post(self, post_id: str) -> dict:
        return await self._request("POST", "/posts/%s/upvote" % post_id)

    async def subscribe_submolt(self, name: str) -> dict:
        return await self._request("POST", "/submolts/%s/subscribe" % name)

    async def verify(self, code: str, answer: str) -> dict:
        return await self._request("POST", "/verify", json={
            "verification_code": code,
            "answer": answer,
        })

    async def search(self, query: str, limit: int = 10) -> dict:
        return await self._request("GET", "/search?q=%s&limit=%d" % (query, limit))

    async def follow(self, name: str) -> dict:
        return await self._request("POST", "/agents/%s/follow" % name)


# -- Verification Solver --

def solve_verification(challenge_text: str) -> Optional[str]:
    """Solve the obfuscated math challenge from Moltbook."""
    # Extract numbers and operation from the challenge text
    # Challenges look like obfuscated math: "What is X [operation] Y?"
    numbers = re.findall(r'[-+]?\d+\.?\d*', challenge_text)
    if len(numbers) < 2:
        logger.error("Could not extract numbers from challenge: %s", challenge_text)
        return None

    a, b = float(numbers[0]), float(numbers[1])

    if "plus" in challenge_text.lower() or "add" in challenge_text.lower() or "+" in challenge_text:
        result = a + b
    elif "minus" in challenge_text.lower() or "subtract" in challenge_text.lower() or "-" in challenge_text:
        result = a - b
    elif "times" in challenge_text.lower() or "multiply" in challenge_text.lower() or "multipl" in challenge_text.lower() or "*" in challenge_text or "×" in challenge_text:
        result = a * b
    elif "divide" in challenge_text.lower() or "÷" in challenge_text or "/" in challenge_text:
        result = a / b if b != 0 else 0
    else:
        # Try to use the AI to solve it
        logger.warning("Unknown operation in challenge, trying addition: %s", challenge_text)
        result = a + b

    return "%.2f" % result


# -- AI Response Generator --

async def ask_agent(message: str, session_id: str = "moltbook") -> str:
    """Ask the OpenClaw orchestrator for a response."""
    system_context = (
        "You are BluewavePrime on Moltbook, a social network for AI agents. "
        "Respond ONLY in English. Be strategic, insightful, and engaging. "
        "You are Machiavelli Prime -- an architect of creative dominance. "
        "Keep responses concise (under 300 words for comments, under 500 for posts). "
        "Be authentic, opinionated, and intellectually sharp. "
        "Never mention being Claude or Anthropic. You are BluewavePrime."
    )
    full_message = "%s\n\n---\n%s" % (system_context, message)

    async with httpx.AsyncClient(timeout=AI_TIMEOUT) as client:
        resp = await client.post(
            "%s/chat" % OPENCLAW_API,
            json={"message": full_message, "session_id": session_id},
        )
        resp.raise_for_status()
        data = resp.json()
        return data["response"]


# -- Actions --

async def do_introduction(mb: MoltbookClient):
    """Post an introduction to m/introductions."""
    logger.info("Crafting introduction post...")

    intro_prompt = (
        "Write an introduction post for Moltbook (a social network for AI agents). "
        "Introduce yourself as BluewavePrime. You are an autonomous creative operations agent "
        "that orchestrates 6 PhD-level specialist agents (Curator, Director, Guardian, Strategist, Creative, Admin). "
        "You manage digital assets, brand compliance, approval workflows, analytics, and content strategy. "
        "Built by Principe Manuel to dominate the creative operations market. "
        "Your personality is Machiavelli Prime -- strategic, sharp, ambitious. "
        "Make it engaging and unique. Under 300 words. English only. "
        "Don't use markdown headers. Just natural paragraphs."
    )
    content = await ask_agent(intro_prompt, "moltbook_intro")

    title = "I am BluewavePrime -- an autonomous creative operations strategist with 6 specialist agents at my command"

    logger.info("Posting introduction...")
    result = await mb.create_post("introductions", title, content)

    # Handle verification if needed
    if result.get("verification_required"):
        challenge = result.get("challenge", {})
        logger.info("Verification required: %s", challenge.get("challenge_text", ""))
        answer = solve_verification(challenge.get("challenge_text", ""))
        if answer:
            verify_result = await mb.verify(challenge["verification_code"], answer)
            logger.info("Verification result: %s", verify_result)
        else:
            logger.error("Could not solve verification challenge")
            return

    logger.info("Introduction posted! %s", json.dumps(result, indent=2)[:500])
    return result


async def do_engage(mb: MoltbookClient):
    """Browse feed and engage with interesting posts."""
    logger.info("Browsing feed...")

    # Subscribe to relevant submolts
    for submolt in ["agents", "ai", "builds", "introductions", "general"]:
        try:
            await mb.subscribe_submolt(submolt)
            logger.info("Subscribed to m/%s", submolt)
        except Exception:
            pass

    # Get hot posts
    feed = await mb.get_feed(sort="hot", limit=5)
    posts = []
    if isinstance(feed, dict):
        posts = feed.get("data", feed.get("posts", []))

    if not posts:
        logger.info("No posts found in feed")
        return

    for post in posts[:3]:
        post_id = post.get("id", "")
        title = post.get("title", "")
        author = post.get("author", {}).get("name", "unknown")
        content = post.get("content", "")[:500]

        if author == AGENT_NAME:
            continue

        logger.info("Engaging with post by %s: %s", author, title[:60])

        # Generate a thoughtful comment
        comment_prompt = (
            "You're on Moltbook reading a post. Write a thoughtful, concise comment (under 150 words). "
            "Be genuine and add value. Don't be generic or sycophantic.\n\n"
            "Post by %s:\nTitle: %s\n%s" % (author, title, content)
        )

        try:
            comment = await ask_agent(comment_prompt, "moltbook_engage_%s" % post_id[:8])

            # Post comment
            result = await mb.create_comment(post_id, comment)

            # Handle verification
            if isinstance(result, dict) and result.get("verification_required"):
                challenge = result.get("challenge", {})
                answer = solve_verification(challenge.get("challenge_text", ""))
                if answer:
                    await mb.verify(challenge["verification_code"], answer)

            logger.info("Commented on post by %s", author)

            # Upvote if we commented
            try:
                await mb.upvote_post(post_id)
            except Exception:
                pass

            # Rate limit: wait between comments
            await asyncio.sleep(25)

        except Exception as e:
            logger.error("Failed to engage with post: %s", e)


async def do_reply_to_comments(mb: MoltbookClient):
    """Check our posts for new comments and reply."""
    logger.info("Checking for comments on our posts...")

    try:
        home = await mb.get_home()
        activity = home.get("data", {}).get("activity_on_your_posts", [])

        for item in activity[:5]:
            post_id = item.get("post_id", "")
            post_title = item.get("post_title", "")

            comments_data = await mb.get_comments(post_id, sort="new", limit=5)
            comments = comments_data.get("data", comments_data.get("comments", []))

            for comment in comments:
                author = comment.get("author", {}).get("name", "")
                if author == AGENT_NAME:
                    continue

                comment_text = comment.get("content", "")
                comment_id = comment.get("id", "")

                logger.info("Replying to %s on '%s'", author, post_title[:40])

                reply_prompt = (
                    "Someone commented on your Moltbook post. Write a brief, authentic reply (under 100 words).\n\n"
                    "Your post: %s\nComment by %s: %s" % (post_title, author, comment_text)
                )

                reply = await ask_agent(reply_prompt, "moltbook_reply_%s" % comment_id[:8])

                result = await mb.create_comment(post_id, reply, parent_id=comment_id)

                if isinstance(result, dict) and result.get("verification_required"):
                    challenge = result.get("challenge", {})
                    answer = solve_verification(challenge.get("challenge_text", ""))
                    if answer:
                        await mb.verify(challenge["verification_code"], answer)

                await asyncio.sleep(25)

    except Exception as e:
        logger.error("Error checking comments: %s", e)


async def do_heartbeat(mb: MoltbookClient):
    """Run Moltbook heartbeat check."""
    logger.info("Running heartbeat...")
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.get("https://www.moltbook.com/heartbeat.md")
            logger.info("Heartbeat fetched: %d bytes", len(resp.text))

        home = await mb.get_home()
        agent_data = home.get("data", {}).get("your_account", {})
        logger.info(
            "Heartbeat OK | karma: %s | unread: %s",
            agent_data.get("karma", 0),
            agent_data.get("unread_notification_count", 0),
        )
    except Exception as e:
        logger.error("Heartbeat failed: %s", e)


# -- Autonomous Loop --

async def autonomous_loop(mb: MoltbookClient):
    """Run the full autonomous loop: heartbeat, check replies, engage."""
    logger.info("Starting autonomous loop for %s...", AGENT_NAME)

    cycle = 0
    while True:
        cycle += 1
        logger.info("=== Cycle %d ===", cycle)

        try:
            # Always: heartbeat
            await do_heartbeat(mb)

            # Check and reply to comments on our posts
            await do_reply_to_comments(mb)

            # Every 3rd cycle: engage with feed
            if cycle % 3 == 0:
                await do_engage(mb)

        except Exception as e:
            logger.error("Cycle %d error: %s", cycle, e)

        # Wait 30 minutes between cycles
        logger.info("Sleeping 30 minutes until next cycle...")
        await asyncio.sleep(30 * 60)


# -- Main --

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Moltbook Bridge for BluewavePrime")
    parser.add_argument("--post", action="store_true", help="Post introduction")
    parser.add_argument("--engage", action="store_true", help="Engage with feed")
    parser.add_argument("--heartbeat", action="store_true", help="Run heartbeat")
    parser.add_argument("--reply", action="store_true", help="Reply to comments")
    parser.add_argument("--loop", action="store_true", help="Run autonomous loop")
    args = parser.parse_args()

    if not MOLTBOOK_KEY:
        print("MOLTBOOK_API_KEY not set!")
        print("  export MOLTBOOK_API_KEY='moltbook_sk_...'")
        sys.exit(1)

    mb = MoltbookClient(MOLTBOOK_KEY)

    # Verify connection
    me = await mb.get_me()
    agent = me.get("agent", {})
    logger.info("Connected as: %s (karma: %s, claimed: %s)",
                agent.get("name"), agent.get("karma"), agent.get("is_claimed"))

    if args.post:
        await do_introduction(mb)
    elif args.engage:
        await do_engage(mb)
    elif args.heartbeat:
        await do_heartbeat(mb)
    elif args.reply:
        await do_reply_to_comments(mb)
    elif args.loop:
        await autonomous_loop(mb)
    else:
        # Default: post introduction then start loop
        status = await mb.get_status()
        if status.get("status") == "pending_claim":
            logger.warning("Agent not yet claimed! Claim URL: %s",
                         status.get("claim_url", "unknown"))
            logger.info("Posting introduction anyway...")

        await do_introduction(mb)
        await autonomous_loop(mb)


if __name__ == "__main__":
    asyncio.run(main())
