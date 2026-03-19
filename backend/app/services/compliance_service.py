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
import uuid
from dataclasses import dataclass, field

# Cache built guidelines text per tenant: {tenant_id: (text, expires_at)}
_guidelines_cache: dict[uuid.UUID, tuple[str, float]] = {}
_GUIDELINES_TTL = 300  # 5 minutes

from app.core.config import settings
from app.core.prompt_safety import sanitize_for_prompt, wrap_user_input, strip_markdown_codeblock
from app.core.retry import retry
from app.core.tracing import trace_llm_call
from app.models.brand_guideline import BrandGuideline
from app.prompts import load_prompt

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


# Tool schema for structured compliance output — guarantees valid JSON
COMPLIANCE_RESULT_TOOL = {
    "name": "compliance_result",
    "description": "Return the brand compliance analysis result.",
    "input_schema": {
        "type": "object",
        "properties": {
            "score": {
                "type": "integer",
                "description": "Compliance score from 0 to 100",
            },
            "summary": {
                "type": "string",
                "description": "One sentence overall assessment",
            },
            "issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "string", "enum": ["error", "warning", "info"]},
                        "category": {"type": "string", "enum": ["color", "logo", "tone", "font", "hashtag", "general"]},
                        "message": {"type": "string"},
                        "suggestion": {"type": "string"},
                    },
                    "required": ["severity", "category", "message", "suggestion"],
                },
            },
        },
        "required": ["score", "summary", "issues"],
    },
}


def _build_guidelines_prompt(guidelines: BrandGuideline) -> str:
    """Convert brand guidelines into a structured prompt section.

    Cached per tenant for 5 minutes — guidelines change rarely.
    Saves ~500 tokens per repeated compliance check.
    """
    tenant_id = getattr(guidelines, "tenant_id", None)
    if tenant_id:
        now = time.time()
        cached = _guidelines_cache.get(tenant_id)
        if cached and cached[1] > now:
            return cached[0]

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
        safe_rules = sanitize_for_prompt(json.dumps(guidelines.custom_rules), max_length=1000)
        parts.append(f"CUSTOM RULES: {safe_rules}")

    result = "\n\n".join(parts) if parts else "No specific guidelines defined."

    # Cache for next time
    if tenant_id:
        _guidelines_cache[tenant_id] = (result, time.time() + _GUIDELINES_TTL)

    return result


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
        "text": (
            "Analyze this media asset for brand compliance.\n\n"
            f"BRAND GUIDELINES:\n{guidelines_text}\n\n"
            f"ASSET METADATA:\n{asset_info}\n\n"
            "Score this asset from 0 to 100 for brand compliance. Check:\n"
            "1. Visual alignment with brand colors (if image provided)\n"
            "2. Caption tone matches brand voice guidelines\n"
            "3. Hashtags are appropriate and on-brand\n"
            "4. No violations of the DON'T rules\n"
            "5. Adherence to the DO rules\n\n"
            "Use the compliance_result tool to return your analysis."
        ),
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
                tools=[COMPLIANCE_RESULT_TOOL],
                tool_choice={"type": "tool", "name": "compliance_result"},
            )
            duration_ms = round((time.perf_counter() - t0) * 1000, 1)

            # Extract structured data from tool_use block
            data = None
            for block in resp.content:
                if hasattr(block, "type") and block.type == "tool_use" and block.name == "compliance_result":
                    data = block.input
                    break

            if not data or not isinstance(data, dict):
                # Fallback: try text-based parsing
                raw = resp.content[0].text if resp.content and hasattr(resp.content[0], "text") else ""
                run.log_output({
                    "raw_response": str(raw)[:200],
                    "json_parse_success": False,
                    "used_fallback": True,
                    "duration_ms": duration_ms,
                })
                run.add_tags(["fallback", "tool-use-failure"])
                raise ValueError("Claude did not return structured compliance result")

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
