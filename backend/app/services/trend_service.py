"""Trend Intelligence Service.

Fetches trending topics from Google Trends (via pytrends) and X/Twitter
(via API v2), scores relevance to the tenant's niche, and generates
AI-powered content suggestions using Claude.

Design:
  - Each source has a dedicated fetcher that returns normalized TrendData
  - Sources are combined and deduplicated
  - Claude analyzes trends against the tenant's existing content
  - Results are stored in trend_entries for the dashboard
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import settings
from app.core.retry import retry

logger = logging.getLogger("bluewave.trends")


@dataclass
class TrendData:
    keyword: str
    source: str
    volume: int = 0
    volume_change_pct: float = 0.0
    sentiment_score: float | None = None
    region: str = "US"
    category: str | None = None
    raw_data: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Google Trends fetcher (pytrends)
# ---------------------------------------------------------------------------

@retry(max_retries=2, base_delay=3.0)
async def fetch_google_trends(
    keywords: list[str] | None = None,
    region: str = "US",
    category: int = 0,
) -> list[TrendData]:
    """Fetch trending searches from Google Trends.

    Uses pytrends (unofficial API). Falls back gracefully if unavailable.
    If no keywords provided, fetches today's trending searches.
    """
    try:
        from pytrends.request import TrendReq

        pytrends = TrendReq(hl="en-US", tz=360)

        results: list[TrendData] = []

        if keywords:
            # Interest over time for specific keywords
            pytrends.build_payload(keywords[:5], cat=category, timeframe="now 7-d", geo=region)
            iot = pytrends.interest_over_time()
            if not iot.empty:
                for kw in keywords[:5]:
                    if kw in iot.columns:
                        series = iot[kw]
                        current = int(series.iloc[-1]) if len(series) > 0 else 0
                        prev = int(series.iloc[-7]) if len(series) > 7 else current
                        change = ((current - prev) / max(prev, 1)) * 100
                        results.append(TrendData(
                            keyword=kw,
                            source="google_trends",
                            volume=current,
                            volume_change_pct=round(change, 1),
                            region=region,
                            raw_data={"interest_values": series.tail(7).tolist()},
                        ))
        else:
            # Today's trending searches
            trending = pytrends.trending_searches(pn=region.lower())
            for _, row in trending.head(20).iterrows():
                kw = str(row.iloc[0])
                results.append(TrendData(
                    keyword=kw,
                    source="google_trends",
                    volume=100,
                    volume_change_pct=0.0,
                    region=region,
                ))

        logger.info("Google Trends: fetched %d trends", len(results))
        return results

    except ImportError:
        logger.warning("pytrends not installed — skipping Google Trends")
        return []
    except Exception:
        logger.exception("Google Trends fetch failed")
        return []


# ---------------------------------------------------------------------------
# X/Twitter fetcher (API v2)
# ---------------------------------------------------------------------------

@retry(max_retries=2, base_delay=3.0)
async def fetch_x_trends(
    keywords: list[str] | None = None,
    bearer_token: str | None = None,
) -> list[TrendData]:
    """Fetch trending data from X/Twitter API v2.

    Requires X_BEARER_TOKEN in settings or passed directly.
    Free tier: very limited. Basic ($100/mo): 10k tweets, 7-day search.
    Falls back gracefully if no token configured.
    """
    token = bearer_token or getattr(settings, "X_BEARER_TOKEN", "")
    if not token:
        logger.info("X_BEARER_TOKEN not set — skipping X/Twitter trends")
        return []

    results: list[TrendData] = []
    headers = {"Authorization": f"Bearer {token}"}

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
            if keywords:
                # Search recent tweets for each keyword
                for kw in keywords[:5]:
                    resp = await client.get(
                        "https://api.x.com/2/tweets/search/recent",
                        params={
                            "query": kw,
                            "max_results": 10,
                            "tweet.fields": "public_metrics,created_at",
                        },
                        headers=headers,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        tweets = data.get("data", [])
                        total_engagement = sum(
                            t.get("public_metrics", {}).get("like_count", 0)
                            + t.get("public_metrics", {}).get("retweet_count", 0)
                            for t in tweets
                        )
                        # Simple sentiment: positive if high engagement
                        sentiment = min(total_engagement / max(len(tweets), 1) / 100, 1.0)
                        results.append(TrendData(
                            keyword=kw,
                            source="x_twitter",
                            volume=len(tweets),
                            sentiment_score=round(sentiment, 2),
                            raw_data={"tweet_count": len(tweets), "total_engagement": total_engagement},
                        ))
                    elif resp.status_code == 429:
                        logger.warning("X API rate limited")
                        break
                    else:
                        logger.warning("X API error %d for '%s'", resp.status_code, kw)
            else:
                # Get trending topics (requires elevated access)
                # WOEID 1 = worldwide, 23424977 = US
                resp = await client.get(
                    "https://api.x.com/2/trends/by/woeid/23424977",
                    headers=headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for trend in data.get("data", [])[:20]:
                        results.append(TrendData(
                            keyword=trend.get("trend_name", trend.get("name", "")),
                            source="x_twitter",
                            volume=trend.get("tweet_count", 0),
                            raw_data=trend,
                        ))

        logger.info("X/Twitter: fetched %d trends", len(results))
        return results

    except Exception:
        logger.exception("X/Twitter fetch failed")
        return []


# ---------------------------------------------------------------------------
# AI-powered trend analysis
# ---------------------------------------------------------------------------

async def analyze_trends_with_ai(
    trends: list[TrendData],
    tenant_niche: str = "marketing and creative content",
    existing_hashtags: list[str] | None = None,
) -> list[dict]:
    """Use Claude to analyze trends and generate content suggestions.

    For each trending topic, the AI generates:
    - Relevance score (0-1) to the tenant's niche
    - Content suggestion (what kind of asset to create)
    - Draft caption
    - Suggested hashtags
    - Urgency window (how many hours until the trend fades)
    """
    if not trends:
        return []

    from app.services.ai_service import ai_service

    trend_list = "\n".join(
        f"- {t.keyword} (source: {t.source}, volume: {t.volume}, change: {t.volume_change_pct:+.0f}%"
        + (f", sentiment: {t.sentiment_score:.1f}" if t.sentiment_score else "")
        + ")"
        for t in trends[:15]
    )

    existing_tags = ", ".join(existing_hashtags[:20]) if existing_hashtags else "none available"

    prompt = f"""You are a trend intelligence analyst for a creative marketing team.

TENANT NICHE: {tenant_niche}
EXISTING HASHTAGS IN USE: {existing_tags}

CURRENT TRENDING TOPICS:
{trend_list}

For each trend that is RELEVANT to the tenant's niche (skip irrelevant ones), provide:

1. keyword: the trend keyword
2. relevance_score: 0.0 to 1.0 (how relevant to the niche)
3. suggestion: what type of content/asset the team should create (1-2 sentences)
4. caption_draft: a ready-to-use caption that leverages the trend
5. hashtags: 5-8 hashtags combining the trend with the niche
6. urgency_hours: estimated hours before this trend fades (4, 8, 12, 24, 48)

Return a JSON array of objects. Only include trends with relevance_score >= 0.3.
Return ONLY the JSON array, no other text."""

    try:
        import json as json_mod

        resp = await ai_service._client.messages.create(
            model=ai_service._model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        # Handle markdown code blocks
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        analyzed = json_mod.loads(raw)
        if isinstance(analyzed, list):
            logger.info("AI analyzed %d relevant trends", len(analyzed))
            return analyzed
    except Exception:
        logger.exception("AI trend analysis failed")

    return []


# ---------------------------------------------------------------------------
# Combined pipeline
# ---------------------------------------------------------------------------

async def discover_trends(
    keywords: list[str] | None = None,
    region: str = "US",
    tenant_niche: str = "marketing and creative content",
    existing_hashtags: list[str] | None = None,
    x_bearer_token: str | None = None,
) -> list[dict]:
    """Full pipeline: fetch from all sources → deduplicate → AI analyze.

    Returns list of analyzed trend objects ready for storage.
    """
    # Fetch from both sources concurrently
    import asyncio

    google_task = fetch_google_trends(keywords=keywords, region=region)
    x_task = fetch_x_trends(keywords=keywords, bearer_token=x_bearer_token)

    google_results, x_results = await asyncio.gather(
        google_task, x_task, return_exceptions=True
    )

    all_trends: list[TrendData] = []
    if isinstance(google_results, list):
        all_trends.extend(google_results)
    if isinstance(x_results, list):
        all_trends.extend(x_results)

    if not all_trends:
        logger.info("No trends fetched from any source")
        return []

    # Deduplicate by keyword (keep highest volume)
    seen: dict[str, TrendData] = {}
    for t in all_trends:
        key = t.keyword.lower().strip()
        if key not in seen or t.volume > seen[key].volume:
            seen[key] = t
    deduped = list(seen.values())

    logger.info("Trends after dedup: %d (from %d raw)", len(deduped), len(all_trends))

    # AI analysis
    analyzed = await analyze_trends_with_ai(
        deduped,
        tenant_niche=tenant_niche,
        existing_hashtags=existing_hashtags,
    )

    # Merge AI analysis back with source data
    trend_map = {t.keyword.lower(): t for t in deduped}
    enriched = []
    for item in analyzed:
        kw = item.get("keyword", "").lower()
        source_data = trend_map.get(kw)
        enriched.append({
            "keyword": item.get("keyword", ""),
            "source": source_data.source if source_data else "combined",
            "volume": source_data.volume if source_data else 0,
            "volume_change_pct": source_data.volume_change_pct if source_data else 0.0,
            "sentiment_score": source_data.sentiment_score if source_data else None,
            "region": region,
            "category": tenant_niche,
            "raw_data": source_data.raw_data if source_data else {},
            "relevance_score": item.get("relevance_score", 0.0),
            "ai_suggestion": item.get("suggestion", ""),
            "ai_caption_draft": item.get("caption_draft", ""),
            "ai_hashtags": item.get("hashtags", []),
            "urgency_hours": item.get("urgency_hours", 24),
        })

    return enriched
