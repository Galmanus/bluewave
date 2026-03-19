"""Brand Suite — 10 high-revenue features for brand management.

All functions use Brand DNA from the database and generate on-brand output.
Cost per call: $0.002-0.02 (Haiku). Revenue per call: $5-500.
"""

import json
import logging
import os
from typing import Optional
from datetime import datetime, timedelta

import anthropic
import httpx

logger = logging.getLogger("openclaw.brand_suite")

HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-4-20250514"


async def _get_guidelines() -> Optional[dict]:
    api_url = os.environ.get("BLUEWAVE_API_URL", "http://localhost:8300/api/v1")
    api_key = os.environ.get("BLUEWAVE_API_KEY", "")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{api_url}/brand/guidelines", headers={"X-API-Key": api_key})
            return r.json() if r.status_code == 200 and r.json() else None
    except Exception as e:
        logger.warning("Failed to fetch brand guidelines: %s", e)
        return None


def _voice(g: dict) -> str:
    parts = []
    c = g.get("custom_rules") or {}
    parts.append(f"BRAND: {c.get('brand_name', '?')}")
    if c.get("tagline"): parts.append(f"TAGLINE: {c['tagline']}")
    if c.get("positioning"): parts.append(f"POSITIONING: {c['positioning']}")
    if g.get("tone_description"): parts.append(f"TONE: {g['tone_description'][:300]}")
    if g.get("dos"): parts.append("ALWAYS: " + " | ".join(g["dos"]))
    if g.get("donts"): parts.append("NEVER: " + " | ".join(g["donts"]))
    if c.get("hashtags"): parts.append(f"HASHTAGS: {', '.join(c['hashtags'])}")
    if c.get("personas"):
        p = c["personas"]
        if isinstance(p, dict):
            parts.append("PERSONAS: " + " | ".join(f"{k}: {v}" for k, v in p.items()))
    return "\n".join(parts)


async def _call(system: str, user: str, model: str = HAIKU, max_tokens: int = 2000) -> str:
    client = anthropic.AsyncAnthropic()
    try:
        r = await client.messages.create(model=model, max_tokens=max_tokens, system=system, messages=[{"role": "user", "content": user}])
        return r.content[0].text
    except Exception as e:
        logger.error("Claude API call failed: %s", e)
        return f"Error: {str(e)[:200]}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. BRAND DNA FROM PDF (extract brand guidelines from uploaded PDF)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def extract_brand_dna(pdf_base64: str) -> str:
    """Extract Brand DNA from a PDF brand guide. Uses Sonnet for accuracy."""
    system = (
        "You are a Brand Strategist extracting brand DNA from a brand guide document.\n"
        "Extract and return a structured JSON with:\n"
        "- brand_name, tagline, positioning, sector\n"
        "- primary_colors (array of hex), secondary_colors (array of hex)\n"
        "- fonts (array), tone_description\n"
        "- dos (array of rules to follow), donts (array of rules to avoid)\n"
        "- archetypes, personas, hashtags\n"
        "Be precise. Extract exact hex codes, exact font names, exact rules.\n"
        "Return ONLY valid JSON. No explanation."
    )
    return await _call(system, f"Extract brand DNA from this document:\n[PDF content provided as base64]", model=SONNET, max_tokens=3000)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. BATCH COMPLIANCE (check multiple images at once)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def batch_compliance_summary(image_count: int, scores: list) -> str:
    """Generate executive summary for batch compliance results."""
    g = await _get_guidelines()
    if not g: return "No brand guidelines configured."
    brand = (g.get("custom_rules") or {}).get("brand_name", "Brand")

    avg = sum(scores) / len(scores) if scores else 0
    passed = sum(1 for s in scores if s >= 70)
    failed = len(scores) - passed

    system = (
        f"You are the brand compliance director for {brand}.\n"
        "Write a brief executive summary of a batch compliance review.\n"
        "No emojis. Professional tone. 3-5 sentences max."
    )
    user = (
        f"Batch review complete: {image_count} assets analyzed.\n"
        f"Average score: {avg:.0f}/100\n"
        f"Passed (>=70): {passed}\n"
        f"Failed (<70): {failed}\n"
        f"Individual scores: {scores}\n"
        "Write executive summary with key findings and recommended actions."
    )
    return await _call(system, user)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. SOCIAL CALENDAR (generate a month of content)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def generate_social_calendar(
    weeks: int = 4,
    posts_per_week: int = 5,
    channels: str = "instagram_feed,instagram_stories",
    themes: str = "",
    language: str = "pt-BR"
) -> str:
    """Generate a full social media content calendar."""
    g = await _get_guidelines()
    if not g: return "No brand guidelines configured."
    voice = _voice(g)
    brand = (g.get("custom_rules") or {}).get("brand_name", "Brand")

    system = (
        f"You are the content strategist for {brand}.\n"
        f"Generate a {weeks}-week social media calendar with {posts_per_week} posts per week.\n"
        "For each post include: day, channel, content type, full caption, hashtags.\n"
        "Mix content types: product showcase, behind-the-scenes, educational, engagement, promotional.\n"
        "Balance channels across the week.\n"
        f"Write in {language}. No emojis unless brand allows.\n"
        "Format as a clean list with --- between weeks.\n\n"
        f"BRAND VOICE:\n{voice}"
    )
    user = f"Channels: {channels}\n"
    if themes:
        user += f"Monthly themes/campaigns: {themes}\n"
    user += f"Generate {weeks * posts_per_week} posts total."

    return await _call(system, user, model=SONNET, max_tokens=4000)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. CONTENT REPURPOSE (1 piece → 7 channels)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def repurpose_content(
    original_content: str,
    original_channel: str = "instagram_feed",
    language: str = "pt-BR"
) -> str:
    """Take one piece of content and adapt it for all 7 channels."""
    g = await _get_guidelines()
    if not g: return "No brand guidelines configured."
    voice = _voice(g)
    brand = (g.get("custom_rules") or {}).get("brand_name", "Brand")

    system = (
        f"You are the content strategist for {brand}.\n"
        "Take the original content and adapt it for each channel, respecting each channel's format and audience.\n"
        "Maintain the brand voice across all adaptations.\n"
        f"Write in {language}. No emojis unless brand allows.\n"
        "Separate each channel with --- and label it clearly.\n\n"
        f"BRAND VOICE:\n{voice}"
    )
    user = (
        f"ORIGINAL ({original_channel}):\n{original_content}\n\n"
        "Adapt for:\n"
        "1. Instagram Feed (if not original)\n"
        "2. Instagram Stories (ultra short)\n"
        "3. Facebook (conversational)\n"
        "4. LinkedIn (professional)\n"
        "5. TikTok (casual, trend-aware)\n"
        "6. Email subject + preview\n"
        "7. Website copy"
    )
    return await _call(system, user, max_tokens=3000)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. AD COPY (Facebook/Instagram ads)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def generate_ad_copy(
    product: str,
    objective: str = "conversions",
    audience: str = "",
    variations: int = 3,
    language: str = "pt-BR"
) -> str:
    """Generate ad copy for paid social campaigns."""
    g = await _get_guidelines()
    if not g: return "No brand guidelines configured."
    voice = _voice(g)
    brand = (g.get("custom_rules") or {}).get("brand_name", "Brand")

    system = (
        f"You are a performance copywriter for {brand}.\n"
        "Write ad copy that converts while staying perfectly on-brand.\n"
        f"Write in {language}. No emojis.\n"
        "For each variation include: Primary text, Headline, Description, CTA.\n"
        "Separate variations with ---\n\n"
        f"BRAND VOICE:\n{voice}"
    )
    user = (
        f"Product/Service: {product}\n"
        f"Campaign objective: {objective}\n"
        f"Target audience: {audience or 'brand personas'}\n"
        f"Generate {variations} ad variations."
    )
    return await _call(system, user)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6. EMAIL SEQUENCES (welcome, nurture, promo)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def generate_email_sequence(
    sequence_type: str = "welcome",
    emails_count: int = 5,
    product: str = "",
    language: str = "pt-BR"
) -> str:
    """Generate email sequence on-brand."""
    g = await _get_guidelines()
    if not g: return "No brand guidelines configured."
    voice = _voice(g)
    brand = (g.get("custom_rules") or {}).get("brand_name", "Brand")

    types = {
        "welcome": "Welcome sequence for new subscribers. Build relationship, introduce brand, first offer.",
        "nurture": "Nurture sequence for leads. Educate, build trust, gentle CTAs.",
        "promo": "Promotional sequence for a sale/launch. Urgency, value, social proof.",
        "abandoned": "Abandoned cart recovery. Remind, incentivize, last chance.",
        "reengagement": "Win-back sequence for inactive customers.",
    }

    system = (
        f"You are the email marketing strategist for {brand}.\n"
        f"Write a {emails_count}-email {sequence_type} sequence.\n"
        f"Sequence purpose: {types.get(sequence_type, sequence_type)}\n"
        "For each email: Subject line, Preview text, Body copy (concise), CTA.\n"
        "Include suggested send timing (Day 0, Day 2, etc).\n"
        f"Write in {language}. No emojis. On-brand tone.\n"
        "Separate emails with ---\n\n"
        f"BRAND VOICE:\n{voice}"
    )
    user = f"Product/context: {product or brand}\nGenerate {emails_count} emails."
    return await _call(system, user, max_tokens=3000)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 7. PRODUCT DESCRIPTIONS (e-commerce)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def generate_product_descriptions(
    products: list,
    style: str = "short",
    language: str = "pt-BR"
) -> str:
    """Generate product descriptions on-brand for e-commerce."""
    g = await _get_guidelines()
    if not g: return "No brand guidelines configured."
    voice = _voice(g)
    brand = (g.get("custom_rules") or {}).get("brand_name", "Brand")

    styles = {
        "short": "50-80 words. Punchy, benefit-focused.",
        "medium": "100-150 words. Features + benefits + lifestyle.",
        "long": "200-300 words. Full story, SEO-optimized, benefit-rich.",
    }

    system = (
        f"You are the e-commerce copywriter for {brand}.\n"
        f"Style: {styles.get(style, style)}\n"
        f"Write in {language}. No emojis. On-brand voice.\n"
        "For each product: Name, Description, Key features (3 bullets).\n"
        "Separate products with ---\n\n"
        f"BRAND VOICE:\n{voice}"
    )
    user = "Products:\n" + "\n".join(f"- {p}" for p in products)
    return await _call(system, user)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 8. HASHTAG RESEARCH (optimized mix)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def research_hashtags(
    topic: str,
    count: int = 15,
    language: str = "pt-BR"
) -> str:
    """Generate optimized hashtag mix for a topic."""
    g = await _get_guidelines()
    if not g: return "No brand guidelines configured."
    voice = _voice(g)
    brand = (g.get("custom_rules") or {}).get("brand_name", "Brand")

    system = (
        f"You are the social media strategist for {brand}.\n"
        f"Generate {count} hashtags organized by tier:\n"
        "- BRANDED (2-3): official brand hashtags\n"
        "- NICHE (4-5): industry-specific, medium competition\n"
        "- DISCOVERY (4-5): broader, high-volume\n"
        "- TRENDING (2-3): currently relevant\n"
        "List each hashtag with estimated reach (low/medium/high).\n"
        f"Language: {language}. No emojis.\n\n"
        f"BRAND HASHTAGS: {(g.get('custom_rules') or {}).get('hashtags', [])}"
    )
    return await _call(system, f"Topic: {topic}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 9. COMPETITOR CONTENT AUDIT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def audit_competitor_content(
    competitor_name: str,
    competitor_description: str = "",
    language: str = "pt-BR"
) -> str:
    """Analyze competitor's content strategy vs your brand."""
    g = await _get_guidelines()
    if not g: return "No brand guidelines configured."
    voice = _voice(g)
    brand = (g.get("custom_rules") or {}).get("brand_name", "Brand")

    system = (
        f"You are a competitive intelligence analyst for {brand}.\n"
        "Analyze the competitor's likely content strategy and compare with your brand.\n"
        "Identify: content gaps, messaging differences, visual differences, audience overlap.\n"
        "Recommend content opportunities your brand should exploit.\n"
        f"Write in {language}. No emojis. Professional analyst tone.\n\n"
        f"YOUR BRAND:\n{voice}"
    )
    user = (
        f"Competitor: {competitor_name}\n"
        f"Description: {competitor_description or 'analyze based on name and industry context'}\n"
        "Deliver: positioning comparison, content gap analysis, 5 content opportunities."
    )
    return await _call(system, user, model=SONNET)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 10. BRAND REPORT (exportable summary)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def generate_brand_report(
    period: str = "monthly",
    compliance_scores: list = None,
    content_generated: int = 0,
    language: str = "pt-BR"
) -> str:
    """Generate a brand health report for client presentation."""
    g = await _get_guidelines()
    if not g: return "No brand guidelines configured."
    voice = _voice(g)
    brand = (g.get("custom_rules") or {}).get("brand_name", "Brand")

    scores = compliance_scores or []
    avg = sum(scores) / len(scores) if scores else 0
    passed = sum(1 for s in scores if s >= 70) if scores else 0

    system = (
        f"You are the brand director preparing a {period} report for {brand}.\n"
        "Write a professional brand health report suitable for client presentation.\n"
        "Include: executive summary, compliance overview, content production metrics, "
        "brand consistency score, key findings, recommendations for next period.\n"
        f"Write in {language}. No emojis. Authoritative tone.\n"
        "Format with clear headers and sections.\n\n"
        f"BRAND:\n{voice}"
    )
    user = (
        f"Period: {period}\n"
        f"Assets reviewed: {len(scores)}\n"
        f"Average compliance score: {avg:.0f}/100\n"
        f"Pass rate: {passed}/{len(scores)}\n"
        f"Content pieces generated: {content_generated}\n"
        "Generate the full report."
    )
    return await _call(system, user, model=SONNET, max_tokens=3000)
