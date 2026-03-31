"""Brand Suite — high-revenue features for brand management powered by Gemini.
"""

import json
import logging
import os
from typing import Optional
from gemini_engine import gemini_call

logger = logging.getLogger("openclaw.brand_suite")

async def _call(system: str, user: str, model: str = "flash") -> str:
    res = await gemini_call(user, system_prompt=system, model=model)
    return res.get("response", "Error in Gemini call.")

async def generate_social_calendar(weeks: int, posts_per_week: int, channels: str, themes: str, language: str) -> str:
    system = f"You are a social media strategist. Generate a {weeks}-week calendar. Language: {language}."
    user = f"Channels: {channels}. Themes: {themes}. Posts/week: {posts_per_week}."
    return await _call(system, user, model="flash")

async def repurpose_content(content: str, channel: str, language: str) -> str:
    system = f"Adapt content for {channel}. Language: {language}."
    return await _call(system, content)

async def generate_ad_copy(product: str, objective: str, audience: str, variations: int, language: str) -> str:
    system = f"Performance copywriter. Product: {product}. Objective: {objective}. Language: {language}."
    user = f"Audience: {audience}. Variations: {variations}."
    return await _call(system, user)

async def generate_email_sequence(sequence_type: str, emails_count: int, product: str, language: str) -> str:
    system = f"Email strategist. Type: {sequence_type}. Count: {emails_count}. Language: {language}."
    return await _call(system, product)

async def generate_product_descriptions(products: list, style: str, language: str) -> str:
    system = f"E-commerce copywriter. Style: {style}. Language: {language}."
    return await _call(system, str(products))

async def research_hashtags(topic: str, count: int, language: str) -> str:
    system = f"Social media strategist. Hashtags for {topic}. Count: {count}."
    return await _call(system, "Generate.")

async def audit_competitor_content(competitor: str, description: str, language: str) -> str:
    system = f"Competitive intelligence analyst. Language: {language}."
    return await _call(system, f"Competitor: {competitor}. Desc: {description}")

async def generate_brand_report(period: str, scores: list, content_generated: int, language: str) -> str:
    system = f"Brand director. Report for {period}. Content generated: {content_generated}. Language: {language}."
    return await _call(system, f"Scores: {scores}")
