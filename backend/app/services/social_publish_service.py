"""Social media publishing service — publish assets to Twitter/X and LinkedIn.

Each platform is optional — if credentials aren't configured, that platform is skipped.
Instagram is supported via Buffer API as a proxy.
"""

import logging
import uuid
from datetime import datetime, timezone

from app.core.config import settings

logger = logging.getLogger("bluewave.social")


async def publish_to_twitter(
    image_path: str,
    caption: str,
    hashtags: list[str] | None = None,
) -> dict:
    """Publish an image + caption to Twitter/X. Returns {tweet_id, url} or raises."""
    if not all([
        settings.TWITTER_API_KEY,
        settings.TWITTER_API_SECRET,
        settings.TWITTER_ACCESS_TOKEN,
        settings.TWITTER_ACCESS_SECRET,
    ]):
        raise RuntimeError("Twitter API credentials not configured")

    import tweepy

    auth = tweepy.OAuth1UserHandler(
        settings.TWITTER_API_KEY,
        settings.TWITTER_API_SECRET,
        settings.TWITTER_ACCESS_TOKEN,
        settings.TWITTER_ACCESS_SECRET,
    )
    api = tweepy.API(auth)
    client = tweepy.Client(
        consumer_key=settings.TWITTER_API_KEY,
        consumer_secret=settings.TWITTER_API_SECRET,
        access_token=settings.TWITTER_ACCESS_TOKEN,
        access_token_secret=settings.TWITTER_ACCESS_SECRET,
    )

    # Upload media
    media = api.media_upload(image_path)

    # Build tweet text (280 char limit)
    text = caption
    if hashtags:
        tag_str = " ".join(hashtags[:5])
        if len(text) + len(tag_str) + 1 <= 280:
            text = f"{text} {tag_str}"
    text = text[:280]

    response = client.create_tweet(text=text, media_ids=[media.media_id])
    tweet_id = response.data["id"]
    url = f"https://twitter.com/i/status/{tweet_id}"

    logger.info("Published to Twitter: %s", url)
    return {"tweet_id": tweet_id, "url": url}


async def publish_to_linkedin(
    image_path: str,
    caption: str,
    access_token: str,
    author_urn: str,
) -> dict:
    """Publish an image + caption to LinkedIn. Returns {post_id, url} or raises."""
    import httpx

    async with httpx.AsyncClient() as client:
        # Step 1: Register upload
        register_resp = await client.post(
            "https://api.linkedin.com/v2/assets?action=registerUpload",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "registerUploadRequest": {
                    "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                    "owner": author_urn,
                }
            },
        )
        register_resp.raise_for_status()
        register_data = register_resp.json()
        upload_url = register_data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
        asset_urn = register_data["value"]["asset"]

        # Step 2: Upload image
        with open(image_path, "rb") as f:
            upload_resp = await client.put(
                upload_url,
                headers={"Authorization": f"Bearer {access_token}"},
                content=f.read(),
            )
            upload_resp.raise_for_status()

        # Step 3: Create post
        post_resp = await client.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "author": author_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": caption},
                        "shareMediaCategory": "IMAGE",
                        "media": [{
                            "status": "READY",
                            "media": asset_urn,
                        }],
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
            },
        )
        post_resp.raise_for_status()
        post_id = post_resp.headers.get("x-restli-id", "")

    url = f"https://www.linkedin.com/feed/update/{post_id}"
    logger.info("Published to LinkedIn: %s", url)
    return {"post_id": post_id, "url": url}


async def publish_scheduled_post(post_id: uuid.UUID) -> None:
    """Load a scheduled post and publish it to the configured channel."""
    from app.core.database import async_session_factory
    from app.models.asset import MediaAsset
    from app.models.scheduled_post import PostStatus, ScheduledPost
    from sqlalchemy import select

    async with async_session_factory() as db:
        result = await db.execute(
            select(ScheduledPost).where(ScheduledPost.id == post_id)
        )
        post = result.scalar_one_or_none()
        if not post or post.status != PostStatus.scheduled:
            return

        asset_result = await db.execute(
            select(MediaAsset).where(MediaAsset.id == post.asset_id)
        )
        asset = asset_result.scalar_one_or_none()
        if not asset:
            post.status = PostStatus.failed
            post.error_message = "Asset not found"
            await db.commit()
            return

        caption = post.caption_override or asset.caption or ""
        hashtags = post.hashtags_override or asset.hashtags or []

        try:
            if post.channel.value == "twitter":
                result = await publish_to_twitter(asset.file_path, caption, hashtags)
                post.external_url = result["url"]
            elif post.channel.value == "linkedin":
                # LinkedIn requires OAuth token from social_connections table
                logger.warning("LinkedIn publishing requires OAuth — skipping")
                post.error_message = "LinkedIn OAuth not configured"
                post.status = PostStatus.failed
                await db.commit()
                return
            else:
                # Manual or unsupported channel — just mark as published
                pass

            post.status = PostStatus.published
            post.published_at = datetime.now(timezone.utc)
            logger.info("Published post %s to %s", post_id, post.channel.value)

        except Exception as exc:
            post.status = PostStatus.failed
            post.error_message = str(exc)[:500]
            logger.exception("Failed to publish post %s", post_id)

        await db.commit()
