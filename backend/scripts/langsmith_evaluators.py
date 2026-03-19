"""LangSmith evaluators for Bluewave AI quality assessment.

Rule-based evaluators run on every trace. LLM-based evaluators run on a sample.

Usage:
    # Run evaluators against a dataset
    python -m scripts.langsmith_evaluators --dataset bluewave-caption-eval

    # Or import and use in code
    from scripts.langsmith_evaluators import caption_format_check
"""

import json
import re


# ── Rule-based evaluators ──────────────────────────────────────────────────


def caption_format_check(output: str) -> dict:
    """Validate caption format. Returns {score: 0|1, reasoning: str}."""
    issues = []

    if not output or not output.strip():
        return {"score": 0, "reasoning": "Caption is empty"}

    if len(output) > 280:
        issues.append(f"Too long ({len(output)} chars, max 280)")

    if "#" in output:
        issues.append("Contains hashtags in caption body")

    if output.startswith('"') and output.endswith('"'):
        issues.append("Wrapped in quotes")
    if output.startswith("'") and output.endswith("'"):
        issues.append("Wrapped in single quotes")

    if output.lower().startswith("here is") or output.lower().startswith("here's"):
        issues.append("Starts with 'Here is' — prompt artifact")

    if output.startswith("Creative asset:"):
        issues.append("Is the fallback caption")

    if issues:
        return {"score": 0, "reasoning": "; ".join(issues)}
    return {"score": 1, "reasoning": "All format checks passed"}


def hashtags_format_check(output: str) -> dict:
    """Validate hashtags output format. Returns {score: 0|1, reasoning: str}."""
    issues = []

    # Try parsing as JSON
    try:
        tags = json.loads(output)
    except (json.JSONDecodeError, TypeError):
        return {"score": 0, "reasoning": "Not valid JSON"}

    if not isinstance(tags, list):
        return {"score": 0, "reasoning": f"Expected JSON array, got {type(tags).__name__}"}

    if len(tags) < 6:
        issues.append(f"Too few hashtags ({len(tags)}, min 6)")
    if len(tags) > 10:
        issues.append(f"Too many hashtags ({len(tags)}, max 10)")

    non_strings = [t for t in tags if not isinstance(t, str)]
    if non_strings:
        issues.append(f"{len(non_strings)} non-string elements")

    str_tags = [t for t in tags if isinstance(t, str)]
    missing_hash = [t for t in str_tags if not t.startswith("#")]
    if missing_hash:
        issues.append(f"{len(missing_hash)} tags missing # prefix")

    if len(set(t.lower() for t in str_tags)) < len(str_tags):
        issues.append("Contains duplicate hashtags")

    long_tags = [t for t in str_tags if len(t) > 30]
    if long_tags:
        issues.append(f"{len(long_tags)} tags exceed 30 chars")

    # Check for default fallback
    fallback = {"#creative", "#content", "#branding", "#marketing", "#digital"}
    if set(t.lower() for t in str_tags) == fallback:
        issues.append("Contains only fallback default hashtags")

    if issues:
        return {"score": 0, "reasoning": "; ".join(issues)}
    return {"score": 1, "reasoning": "All format checks passed"}


def compliance_format_check(output: str) -> dict:
    """Validate compliance JSON output. Returns {score: 0|1, reasoning: str}."""
    issues = []

    try:
        data = json.loads(output)
    except (json.JSONDecodeError, TypeError):
        return {"score": 0, "reasoning": "Not valid JSON"}

    if not isinstance(data, dict):
        return {"score": 0, "reasoning": f"Expected JSON object, got {type(data).__name__}"}

    # Score field
    if "score" not in data:
        issues.append("Missing 'score' field")
    elif not isinstance(data["score"], (int, float)):
        issues.append(f"'score' is {type(data['score']).__name__}, expected int")
    elif not (0 <= data["score"] <= 100):
        issues.append(f"Score {data['score']} out of range 0-100")
    elif data["score"] == 50:
        issues.append("Score is 50 — likely a fallback/parse-failure indicator")

    # Summary field
    if "summary" not in data:
        issues.append("Missing 'summary' field")
    elif not isinstance(data["summary"], str) or not data["summary"].strip():
        issues.append("'summary' is empty or not a string")

    # Issues field
    if "issues" not in data:
        issues.append("Missing 'issues' field")
    elif not isinstance(data["issues"], list):
        issues.append(f"'issues' is {type(data['issues']).__name__}, expected array")
    else:
        valid_severities = {"error", "warning", "info"}
        valid_categories = {"color", "logo", "tone", "font", "hashtag", "general"}
        for idx, issue in enumerate(data["issues"]):
            if not isinstance(issue, dict):
                issues.append(f"Issue [{idx}] is not an object")
                continue
            sev = issue.get("severity", "")
            if sev not in valid_severities:
                issues.append(f"Issue [{idx}] severity '{sev}' not in {valid_severities}")
            cat = issue.get("category", "")
            if cat not in valid_categories:
                issues.append(f"Issue [{idx}] category '{cat}' not in {valid_categories}")

    if issues:
        return {"score": 0, "reasoning": "; ".join(issues)}
    return {"score": 1, "reasoning": "All format checks passed"}


# ── LLM-based evaluator prompt ────────────────────────────────────────────

CAPTION_QUALITY_EVAL_PROMPT = """You are evaluating the quality of an AI-generated social media caption.

ORIGINAL CONTEXT:
Filename: {filename}
File type: {file_type}

GENERATED CAPTION:
{caption}

Rate the caption 1-5 on each dimension:
1. Professional tone (1=unprofessional, 5=highly professional)
2. Relevance to the described content (1=irrelevant, 5=highly relevant)
3. Engagement potential (1=boring, 5=very engaging)
4. Brand-friendliness (1=inappropriate for brands, 5=perfectly brand-safe)

Return ONLY a JSON object:
{{"overall_score": <1-5 average>, "professional_tone": <1-5>, "relevance": <1-5>, "engagement": <1-5>, "brand_friendly": <1-5>, "reasoning": "<1-2 sentences>"}}"""


if __name__ == "__main__":
    # Quick self-test
    print("=== Caption Format Check ===")
    print(caption_format_check("A stunning visual that captures your brand story."))
    print(caption_format_check(""))
    print(caption_format_check("Here is a caption for your image #branding"))
    print(caption_format_check("Creative asset: test.jpg"))

    print("\n=== Hashtags Format Check ===")
    print(hashtags_format_check('["#branding", "#design", "#creative", "#marketing", "#social", "#content"]'))
    print(hashtags_format_check("not json"))
    print(hashtags_format_check('["#creative", "#content", "#branding", "#marketing", "#digital"]'))

    print("\n=== Compliance Format Check ===")
    print(compliance_format_check('{"score": 85, "summary": "Good compliance", "issues": []}'))
    print(compliance_format_check('{"score": 50, "summary": "Error", "issues": []}'))
    print(compliance_format_check("not json"))
