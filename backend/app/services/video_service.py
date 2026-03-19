"""Video analysis service — extract keyframes and analyze with Claude Vision.

Extracts N keyframes from uploaded videos using OpenCV, then sends them to
Claude Vision as a multi-image message for contextual caption generation.
"""

import base64
import logging
import os
import tempfile

logger = logging.getLogger("bluewave.video")


def extract_keyframes(video_path: str, num_frames: int = 5) -> list[str]:
    """Extract evenly-spaced keyframes from a video. Returns list of temp JPEG paths."""
    try:
        import cv2
    except ImportError:
        logger.warning("opencv-python-headless not installed — skipping video analysis")
        return []

    frames: list[str] = []
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        logger.warning("Cannot open video: %s", video_path)
        return []

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames < num_frames:
        num_frames = max(1, total_frames)

    interval = total_frames // num_frames

    for i in range(num_frames):
        frame_pos = i * interval
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
        ret, frame = cap.read()
        if not ret:
            continue

        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        cv2.imwrite(tmp.name, frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        frames.append(tmp.name)

    cap.release()
    logger.info("Extracted %d keyframes from %s", len(frames), video_path)
    return frames


async def analyze_video(video_path: str, filename: str) -> tuple[str, list[str]]:
    """Analyze video by extracting keyframes and sending to Claude Vision.

    Returns (caption, hashtags).
    """
    import anthropic
    from app.core.config import settings

    frames = extract_keyframes(video_path, num_frames=5)
    if not frames:
        return f"Dynamic video content: {filename}", ["#video", "#content", "#creative"]

    try:
        # Build multi-image message
        content: list[dict] = []
        for frame_path in frames:
            with open(frame_path, "rb") as f:
                b64 = base64.standard_b64encode(f.read()).decode("ascii")
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
            })

        content.append({
            "type": "text",
            "text": (
                f"These are {len(frames)} keyframes extracted from a video named \"{filename}\". "
                "Describe what happens in the video and generate a single engaging caption "
                "suitable for social media. Reply ONLY with the caption text."
            ),
        })

        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        resp = await client.messages.create(
            model=settings.AI_MODEL,
            max_tokens=300,
            messages=[{"role": "user", "content": content}],
            system=(
                "You are a creative marketing copywriter. Generate a concise, "
                "engaging caption for this video content. Be professional and brand-friendly."
            ),
        )
        caption = resp.content[0].text.strip()

        # Also generate hashtags
        hash_resp = await client.messages.create(
            model=settings.AI_MODEL,
            max_tokens=200,
            messages=[{"role": "user", "content": content[:len(frames)] + [{
                "type": "text",
                "text": f"Generate 6-10 relevant hashtags for this video. Return ONLY a JSON array of strings starting with #.",
            }]}],
            system="You are a social media strategist. Return ONLY a JSON array of hashtag strings.",
        )

        import json
        try:
            hashtags = json.loads(hash_resp.content[0].text.strip())
            if isinstance(hashtags, list):
                hashtags = [t if t.startswith("#") else f"#{t}" for t in hashtags if isinstance(t, str)]
            else:
                hashtags = ["#video", "#content", "#creative"]
        except (json.JSONDecodeError, ValueError):
            hashtags = ["#video", "#content", "#creative"]

        return caption, hashtags

    except Exception:
        logger.exception("Video analysis failed for %s", filename)
        return f"Dynamic video content: {filename}", ["#video", "#content", "#creative"]

    finally:
        # Clean up temp frames
        for frame_path in frames:
            try:
                os.unlink(frame_path)
            except OSError:
                pass
