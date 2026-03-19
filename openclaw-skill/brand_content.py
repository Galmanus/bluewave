"""On-brand content generation using Brand DNA.

Generates captions, copies, hashtags, and content variations
that are pre-validated against the brand's voice, tone, and rules.

Cost: ~$0.002 per generation (Haiku).
"""

import json
import logging
import os
from typing import Optional

import anthropic
import httpx

logger = logging.getLogger("openclaw.brand_content")

HAIKU = "claude-haiku-4-5-20251001"


async def get_brand_guidelines() -> Optional[dict]:
    """Fetch brand guidelines from Bluewave API."""
    api_url = os.environ.get("BLUEWAVE_API_URL", "http://localhost:8300/api/v1")
    api_key = os.environ.get("BLUEWAVE_API_KEY", "")
    if not api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{api_url}/brand/guidelines",
                headers={"X-API-Key": api_key},
            )
            if resp.status_code == 200:
                return resp.json() or None
    except Exception as e:
        logger.error("Failed to fetch brand guidelines: %s", e)
    return None


def build_voice_prompt(guidelines: dict) -> str:
    """Build brand voice instructions from guidelines."""
    parts = []
    custom = guidelines.get("custom_rules") or {}

    brand_name = custom.get("brand_name", "the brand")
    parts.append(f"BRAND: {brand_name}")

    if custom.get("tagline"):
        parts.append(f"TAGLINE: {custom['tagline']}")
    if custom.get("positioning"):
        parts.append(f"POSITIONING: {custom['positioning']}")
    if guidelines.get("tone_description"):
        parts.append(f"TONE: {guidelines['tone_description'][:300]}")
    if guidelines.get("dos"):
        parts.append("ALWAYS: " + " | ".join(guidelines["dos"]))
    if guidelines.get("donts"):
        parts.append("NEVER: " + " | ".join(guidelines["donts"]))
    if custom.get("hashtags"):
        parts.append(f"OFFICIAL HASHTAGS: {', '.join(custom['hashtags'])}")
    if custom.get("archetypes"):
        parts.append(f"ARCHETYPES: {', '.join(custom['archetypes'])}")
    if custom.get("personas"):
        personas = custom["personas"]
        if isinstance(personas, dict):
            parts.append("PERSONAS: " + " | ".join(f"{k}: {v}" for k, v in personas.items()))

    return "\n".join(parts)


async def generate_content(
    content_type: str,
    context: str = "",
    channel: str = "instagram_feed",
    language: str = "pt-BR",
    variations: int = 1,
) -> str:
    """Generate on-brand content.

    Args:
        content_type: caption, stories, headline, cta, description, hashtags
        context: what the content is about (product, campaign, image description)
        channel: instagram_feed, instagram_stories, facebook, linkedin, tiktok, email, website
        language: output language
        variations: number of variations to generate (1-5)
    """
    guidelines = await get_brand_guidelines()
    if not guidelines:
        return "No brand guidelines configured. Set up Brand DNA first."

    voice = build_voice_prompt(guidelines)
    custom = guidelines.get("custom_rules") or {}
    brand_name = custom.get("brand_name", "the brand")

    channel_rules = ""
    channel_specs = {
        "instagram_feed": "Max 2200 chars. First line hooks attention. Line breaks for readability. 3-8 hashtags at end.",
        "instagram_stories": "Very short. 1-2 lines max. Punchy. CTA or question to drive engagement.",
        "facebook": "Conversational. Can be longer. Question or story format works well.",
        "linkedin": "Professional but accessible. Thought leadership angle. No hashtag spam.",
        "tiktok": "Ultra casual. Trend-aware. Short and punchy. Speak like the audience.",
        "email": "Subject line + preview text + body. Personalized. Clear CTA.",
        "website": "SEO-aware. Clear value proposition. Scannable with headers.",
    }
    channel_rules = channel_specs.get(channel, "Adapt to the channel's best practices.")

    type_instructions = {
        "caption": f"Write a post caption for {channel}.",
        "stories": "Write copy for Instagram Stories. Ultra short, engaging, swipe-up worthy.",
        "headline": "Write a headline. Punchy, memorable, on-brand.",
        "cta": "Write a call-to-action. Clear, compelling, action-oriented.",
        "description": "Write a product/service description. Benefits-focused, on-brand voice.",
        "hashtags": f"Generate 8-12 hashtags for {channel}. Mix branded + discovery + niche.",
    }
    type_inst = type_instructions.get(content_type, f"Write {content_type} content.")

    system_prompt = (
        f"You are the copywriter for {brand_name}. You write EXACTLY in the brand's voice.\n\n"
        "STRICT RULES:\n"
        "- Never use emojis unless the brand voice explicitly allows them.\n"
        "- Never break any rule in the NEVER list.\n"
        "- Always follow the ALWAYS list.\n"
        "- Match the tone dimensions precisely.\n"
        "- Use official hashtags when generating hashtags.\n"
        "- Sound like a real person, not a robot. Not corporate. Not generic.\n"
        f"- Write in {language}.\n"
        "- Output ONLY the content. No explanations, no labels, no meta-commentary.\n"
        f"- If generating {variations} variations, separate each with ---\n\n"
        f"BRAND VOICE:\n{voice}\n\n"
        f"CHANNEL: {channel}\n"
        f"CHANNEL RULES: {channel_rules}"
    )

    user_message = f"{type_inst}\n\n"
    if context:
        user_message += f"CONTEXT: {context}\n\n"
    if variations > 1:
        user_message += f"Generate {variations} different variations. Separate each with ---\n"

    client = anthropic.Anthropic()

    try:
        response = client.messages.create(
            model=HAIKU,
            max_tokens=1000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text
    except Exception as e:
        logger.error("Content generation failed: %s", e)
        return f"Generation failed: {str(e)[:100]}"
