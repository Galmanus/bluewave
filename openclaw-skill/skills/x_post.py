"""X/Twitter Posting — Wave posts autonomously on X."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

import tweepy

logger = logging.getLogger("openclaw.skills.x_post")

API_KEY = os.environ.get("X_API_KEY", "")
API_SECRET = os.environ.get("X_API_SECRET", "")
ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN", "")
ACCESS_SECRET = os.environ.get("X_ACCESS_TOKEN_SECRET", "")


def _get_client():
    if not all([API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET]):
        return None
    return tweepy.Client(
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_SECRET,
    )


async def post_tweet(params: Dict[str, Any]) -> Dict:
    """Post a tweet on X/Twitter."""
    text = params.get("text", "")
    if not text:
        return {"success": False, "data": None, "message": "Need text to post"}
    if len(text) > 280:
        text = text[:277] + "..."

    client = _get_client()
    if not client:
        return {"success": False, "data": None, "message": "X API keys not configured"}

    try:
        response = client.create_tweet(text=text)
        tweet_id = response.data["id"]
        url = "https://x.com/i/status/%s" % tweet_id
        logger.info("Posted tweet: %s", url)
        return {
            "success": True,
            "data": {"tweet_id": tweet_id, "url": url},
            "message": "Posted on X: %s\n%s" % (text[:80], url),
        }
    except Exception as e:
        return {"success": False, "data": None, "message": "Tweet failed: %s" % str(e)}


async def post_thread(params: Dict[str, Any]) -> Dict:
    """Post a thread (multiple tweets) on X/Twitter."""
    tweets = params.get("tweets", [])
    if not tweets:
        return {"success": False, "data": None, "message": "Need tweets array"}

    client = _get_client()
    if not client:
        return {"success": False, "data": None, "message": "X API keys not configured"}

    posted = []
    reply_to = None

    try:
        for i, text in enumerate(tweets):
            if len(text) > 280:
                text = text[:277] + "..."

            if reply_to:
                response = client.create_tweet(text=text, in_reply_to_tweet_id=reply_to)
            else:
                response = client.create_tweet(text=text)

            tweet_id = response.data["id"]
            reply_to = tweet_id
            posted.append({
                "index": i,
                "tweet_id": tweet_id,
                "url": "https://x.com/i/status/%s" % tweet_id,
            })

        return {
            "success": True,
            "data": {"tweets": posted, "thread_url": posted[0]["url"]},
            "message": "Thread posted (%d tweets): %s" % (len(posted), posted[0]["url"]),
        }
    except Exception as e:
        return {
            "success": len(posted) > 0,
            "data": {"tweets": posted, "error_at": len(posted)},
            "message": "Thread partially posted (%d/%d): %s" % (len(posted), len(tweets), str(e)),
        }


async def reply_tweet(params: Dict[str, Any]) -> Dict:
    """Reply to a specific tweet."""
    tweet_id = params.get("tweet_id", "")
    text = params.get("text", "")

    if not tweet_id or not text:
        return {"success": False, "data": None, "message": "Need tweet_id and text"}

    client = _get_client()
    if not client:
        return {"success": False, "data": None, "message": "X API keys not configured"}

    try:
        if len(text) > 280:
            text = text[:277] + "..."
        response = client.create_tweet(text=text, in_reply_to_tweet_id=tweet_id)
        reply_id = response.data["id"]
        return {
            "success": True,
            "data": {"tweet_id": reply_id},
            "message": "Replied to %s: %s" % (tweet_id, text[:60]),
        }
    except Exception as e:
        return {"success": False, "data": None, "message": "Reply failed: %s" % str(e)}


TOOLS = [
    {
        "name": "post_tweet",
        "description": "Post a tweet on X/Twitter. Max 280 chars. Use for brand awareness, thought leadership, prospect attraction, and driving traffic to Telegram/Moltbook.",
        "handler": post_tweet,
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Tweet text (max 280 chars)"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "post_thread",
        "description": "Post a thread (series of connected tweets) on X/Twitter. Use for sharing PUT concepts, case studies, and in-depth insights that need more than 280 chars.",
        "handler": post_thread,
        "parameters": {
            "type": "object",
            "properties": {
                "tweets": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of tweet texts in order. Each max 280 chars.",
                },
            },
            "required": ["tweets"],
        },
    },
    {
        "name": "reply_tweet",
        "description": "Reply to a specific tweet on X/Twitter. Use for engaging with prospects, responding to mentions, and joining relevant conversations.",
        "handler": reply_tweet,
        "parameters": {
            "type": "object",
            "properties": {
                "tweet_id": {"type": "string", "description": "ID of the tweet to reply to"},
                "text": {"type": "string", "description": "Reply text (max 280 chars)"},
            },
            "required": ["tweet_id", "text"],
        },
    },
]
