"""Brand Compliance Service.

Uses Claude AI to check media assets against tenant brand guidelines.
Returns a compliance score (0-100) and a list of issues found.

The service:
1. Reads the image via Claude Vision (if image type)
2. Compares against the tenant's brand guidelines
3. Returns structured ComplianceResult with score + issues
"""

import base64
import json
import logging
import time
from dataclasses import dataclass, field

from app.core.config import settings
from app.core.retry import retry
from app.core.tracing import trace_llm_call
from app.models.brand_guideline import BrandGuideline

logger = logging.getLogger("bluewave.compliance")


@dataclass
class ComplianceIssue:
    severity: str  # "error" | "warning" | "info"
    category: str  # "color", "logo", "tone", "font", "general"
    message: str
    suggestion: str


@dataclass
class ComplianceResult:
    score: int  # 0-100
    passed: bool  # score >= threshold
    issues: list[ComplianceIssue] = field(default_factory=list)
    summary: str = ""


def _build_guidelines_prompt(guidelines: BrandGuideline) -> str:
    """Convert brand guidelines into a structured prompt section."""
    parts = []

    if guidelines.primary_colors:
        parts.append(f"PRIMARY COLORS: {', '.join(guidelines.primary_colors)}")
    if guidelines.secondary_colors:
        parts.append(f"SECONDARY COLORS: {', '.join(guidelines.secondary_colors)}")
    if guidelines.fonts:
        parts.append(f"APPROVED FONTS: {', '.join(guidelines.fonts)}")
    if guidelines.tone_description:
        parts.append(f"BRAND TONE: {guidelines.tone_description}")
    if guidelines.dos:
        parts.append("DO's:\n" + "\n".join(f"  - {d}" for d in guidelines.dos))
    if guidelines.donts:
        parts.append("DON'Ts:\n" + "\n".join(f"  - {d}" for d in guidelines.donts))
    if guidelines.custom_rules:
        parts.append(f"CUSTOM RULES: {json.dumps(guidelines.custom_rules)}")

    return "\n\n".join(parts) if parts else "No specific guidelines defined."


@retry(max_retries=2, base_delay=2.0)
async def check_compliance(
    file_path: str | None,
    file_type: str,
    caption: str | None,
    hashtags: list[str] | None,
    guidelines: BrandGuideline,
    threshold: int = 70,
) -> ComplianceResult:
    """Check an asset against brand guidelines using Claude AI.

    Args:
        file_path: Path to the media file (for vision analysis)
        file_type: MIME type
        caption: Current caption on the asset
        hashtags: Current hashtags
        guidelines: Tenant's brand guidelines
        threshold: Score at or above which the asset passes

    Returns:
        ComplianceResult with score, pass/fail, issues, and summary
    """
    if not settings.ANTHROPIC_API_KEY:
        logger.warning("No API key — returning default pass")
        return ComplianceResult(score=100, passed=True, summary="Compliance check skipped (no AI configured)")

    import anthropic

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    guidelines_text = _build_guidelines_prompt(guidelines)

    # Build message content
    content: list[dict] = []

    # Add image if available and supported
    vision_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file_path and file_type in vision_types:
        try:
            with open(file_path, "rb") as f:
                img_data = f.read(20 * 1024 * 1024)
            if len(img_data) < 20 * 1024 * 1024:
                b64 = base64.standard_b64encode(img_data).decode("ascii")
                content.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": file_type, "data": b64},
                })
        except OSError:
            logger.warning("Could not read image for compliance: %s", file_path)

    # Build the text prompt
    asset_info = f"Caption: \"{caption or 'No caption'}\""
    if hashtags:
        asset_info += f"\nHashtags: {', '.join(hashtags)}"

    content.append({
        "type": "text",
        "text": f"""Analyze this media asset for brand compliance.

BRAND GUIDELINES:
{guidelines_text}

ASSET METADATA:
{asset_info}

Score this asset from 0 to 100 for brand compliance. Check:
1. Visual alignment with brand colors (if image provided)
2. Caption tone matches brand voice guidelines
3. Hashtags are appropriate and on-brand
4. No violations of the DON'T rules
5. Adherence to the DO rules

Return ONLY a JSON object with this exact structure:
{{
  "score": <0-100>,
  "summary": "<1 sentence overall assessment>",
  "issues": [
    {{
      "severity": "error|warning|info",
      "category": "color|logo|tone|font|hashtag|general",
      "message": "<what's wrong>",
      "suggestion": "<how to fix it>"
    }}
  ]
}}

If the asset is fully compliant, return score 100 and an empty issues array.
Return ONLY the JSON, no other text.""",
    })

    has_image = bool(content and any(b.get("type") == "image" for b in content))
    guideline_fields = []
    for attr in ("primary_colors", "secondary_colors", "fonts", "tone_description", "dos", "donts", "custom_rules"):
        if getattr(guidelines, attr, None):
            guideline_fields.append(attr)

    trace_metadata = {
        "guidelines_present": bool(guideline_fields),
        "guideline_fields": guideline_fields,
        "threshold": threshold,
        "has_caption": bool(caption),
        "has_hashtags": bool(hashtags),
        "has_image": has_image,
    }

    async with trace_llm_call(
        "bluewave.check_compliance",
        inputs={"model": settings.AI_MODEL, "max_tokens": 1000, "guidelines_text": guidelines_text},
        metadata=trace_metadata,
        tags=["compliance", "json-output", "brand-governance", "vision" if has_image else "text-only"],
    ) as run:
        try:
            t0 = time.perf_counter()
            resp = await client.messages.create(
                model=settings.AI_MODEL,
                max_tokens=1000,
                messages=[{"role": "user", "content": content}],
            )
            duration_ms = round((time.perf_counter() - t0) * 1000, 1)
            raw = resp.content[0].text.strip()

            # Handle markdown code blocks
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

            json_parse_ok = False
            try:
                data = json.loads(raw)
                json_parse_ok = True
            except json.JSONDecodeError:
                data = None

            if not json_parse_ok or not isinstance(data, dict):
                run.log_output({
                    "raw_response": raw,
                    "json_parse_success": False,
                    "used_fallback": True,
                    "duration_ms": duration_ms,
                })
                run.add_tags(["fallback", "json-parse-failure"])
                raise ValueError(f"Invalid JSON response from Claude: {raw[:200]}")

            score = int(data.get("score", 0))
            issues = [
                ComplianceIssue(
                    severity=i.get("severity", "info"),
                    category=i.get("category", "general"),
                    message=i.get("message", ""),
                    suggestion=i.get("suggestion", ""),
                )
                for i in data.get("issues", [])
            ]

            result = ComplianceResult(
                score=score,
                passed=score >= threshold,
                issues=issues,
                summary=data.get("summary", ""),
            )

            usage = resp.usage if hasattr(resp, "usage") else None
            issues_by_severity = {}
            for i in issues:
                issues_by_severity[i.severity] = issues_by_severity.get(i.severity, 0) + 1

            run.log_output({
                "raw_response": raw,
                "score": score,
                "passed": result.passed,
                "issues_count": len(issues),
                "issues_by_severity": issues_by_severity,
                "json_parse_success": True,
                "used_fallback": False,
                "input_tokens": getattr(usage, "input_tokens", 0) if usage else 0,
                "output_tokens": getattr(usage, "output_tokens", 0) if usage else 0,
                "model_used": resp.model,
                "duration_ms": duration_ms,
            })

            logger.info("Compliance check: score=%d, passed=%s, issues=%d", score, result.passed, len(issues))
            return result

        except Exception:
            logger.exception("Compliance check failed")
            fallback = ComplianceResult(
                score=50,
                passed=False,
                summary="Compliance check encountered an error — manual review recommended",
                issues=[ComplianceIssue(
                    severity="warning",
                    category="general",
                    message="Automated compliance check failed",
                    suggestion="Please review this asset manually",
                )],
            )
            run.log_output({"score": 50, "used_fallback": True})
            run.add_tags(["fallback"])
            return fallback
