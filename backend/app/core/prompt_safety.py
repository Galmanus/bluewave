"""Prompt safety utilities — prevent injection in AI service calls.

Provides:
- sanitize_for_prompt(): Strip characters that could escape XML delimiters
- wrap_user_input(): Wrap untrusted data in XML tags for Claude
- strip_markdown_codeblock(): Safely extract JSON from Claude responses
"""

import re


def sanitize_for_prompt(value: str, max_length: int = 500) -> str:
    """Sanitize a user-provided string before interpolating into a prompt.

    Removes XML-like tags, control characters, and prompt-injection patterns.
    Truncates to max_length.
    """
    if not value:
        return ""
    # Remove XML/HTML tags that could confuse the model
    value = re.sub(r"</?[a-zA-Z_][^>]*>", "", value)
    # Remove control characters except newlines and tabs
    value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value)
    # Truncate
    return value[:max_length]


def wrap_user_input(tag: str, value: str, max_length: int = 2000) -> str:
    """Wrap untrusted user input in XML delimiters for structured prompt injection defense.

    Example:
        wrap_user_input("filename", "my_photo.jpg")
        → '<filename>my_photo.jpg</filename>'

    The XML structure tells Claude to treat the content as data, not instructions.
    """
    safe_value = sanitize_for_prompt(value, max_length=max_length)
    return f"<{tag}>{safe_value}</{tag}>"


def strip_markdown_codeblock(text: str) -> str:
    """Strip markdown code block wrappers from Claude responses.

    Handles: ```json\n...\n```, ```\n...\n```, and plain text.
    """
    text = text.strip()
    if text.startswith("```"):
        # Remove opening ``` with optional language tag
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        # Remove closing ```
        text = re.sub(r"\n?```$", "", text)
    return text.strip()
