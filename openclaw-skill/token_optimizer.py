"""Token Optimizer — compress tool results and manage token budgets.

Reduces token waste by:
1. Compressing verbose API responses before appending to message history
2. Truncating tool results from older turns
3. Stripping redundant fields from JSON payloads
4. Providing lean summaries of list responses

Typical savings: 60-80% on list responses, 30-50% on detail responses.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("openclaw.token_optimizer")

# Max chars for a tool result in the conversation history
MAX_TOOL_RESULT_CHARS = 1500
# Max chars for tool results from older turns (not the current turn)
MAX_OLD_TOOL_RESULT_CHARS = 400
# Fields to strip from asset objects (verbose, rarely needed by Claude)
STRIP_ASSET_FIELDS = {
    "tenant_id", "created_at", "updated_at", "file_path",
    "file_size", "dimensions", "metadata", "variants",
    "version_history", "comments", "compliance_issues",
}

# Fields to keep for lean asset summaries in lists
LEAN_ASSET_FIELDS = {"id", "status", "caption", "compliance_score", "file_type"}


def compress_tool_result(tool_name: str, result_str: str) -> str:
    """Compress a tool result to minimize token usage.

    Strategy varies by tool type:
    - List operations: Keep only id, status, caption (strip full objects)
    - Detail operations: Strip verbose fields
    - Delegation results: Keep response text, strip metadata
    - Skill results: Keep message, strip raw data
    """
    if len(result_str) <= MAX_TOOL_RESULT_CHARS:
        return result_str

    try:
        data = json.loads(result_str)
    except (json.JSONDecodeError, TypeError):
        return result_str[:MAX_TOOL_RESULT_CHARS] + "..."

    compressed = _compress_by_tool_type(tool_name, data)
    result = json.dumps(compressed, ensure_ascii=False, default=str)

    if len(result) > MAX_TOOL_RESULT_CHARS:
        result = result[:MAX_TOOL_RESULT_CHARS] + "..."

    savings = len(result_str) - len(result)
    if savings > 200:
        logger.debug("Compressed %s: %d -> %d chars (-%d%%)",
                     tool_name, len(result_str), len(result),
                     round(savings / len(result_str) * 100))

    return result


def _compress_by_tool_type(tool_name: str, data: Dict) -> Dict:
    """Apply tool-specific compression strategies."""

    # Asset list responses — keep only lean fields
    if tool_name in ("bluewave_list_assets", "bluewave_search_assets"):
        return _compress_asset_list(data)

    # Asset detail — strip verbose fields
    if tool_name == "bluewave_get_asset":
        return _compress_asset_detail(data)

    # Delegation results — keep response, strip internal metadata
    if tool_name == "delegate_to_agent":
        return _compress_delegation(data)

    # Skill results — keep message, truncate data
    if data.get("data") and isinstance(data["data"], (list, dict)):
        return _compress_skill_result(data)

    # Generic: keep message, truncate data
    return _compress_generic(data)


def _compress_asset_list(data: Dict) -> Dict:
    """Compress asset list: full objects → lean summaries."""
    if not isinstance(data, dict):
        return data

    inner = data.get("data", data)
    items = inner.get("items", []) if isinstance(inner, dict) else []

    if not items:
        return {"success": data.get("success", True), "message": data.get("message", "No assets found.")}

    lean_items = []
    for asset in items:
        lean = {}
        for field in LEAN_ASSET_FIELDS:
            if field in asset:
                val = asset[field]
                if field == "id":
                    val = val[:8]  # Short ID
                elif field == "caption" and val:
                    val = val[:60]  # Truncate caption
                lean[field] = val
        lean_items.append(lean)

    total = inner.get("total", len(items)) if isinstance(inner, dict) else len(items)
    return {
        "success": True,
        "message": data.get("message", ""),
        "data": {"total": total, "items": lean_items},
    }


def _compress_asset_detail(data: Dict) -> Dict:
    """Compress asset detail: strip verbose fields."""
    if not isinstance(data, dict):
        return data

    inner = data.get("data", data)
    if isinstance(inner, dict):
        compressed = {k: v for k, v in inner.items() if k not in STRIP_ASSET_FIELDS}
        if "caption" in compressed and compressed["caption"]:
            compressed["caption"] = compressed["caption"][:120]
        if "id" in compressed:
            compressed["id"] = compressed["id"][:8]
        return {"success": data.get("success", True), "message": data.get("message", ""), "data": compressed}

    return data


def _compress_delegation(data: Dict) -> Dict:
    """Compress delegation result: keep response text, strip verbose metadata."""
    response = data.get("response", "")
    if len(response) > 800:
        response = response[:800] + "..."

    return {
        "success": data.get("success", True),
        "agent": data.get("agent", ""),
        "response": response,
    }


def _compress_skill_result(data: Dict) -> Dict:
    """Compress skill result: keep message, truncate data payload."""
    message = data.get("message", "")
    if len(message) > 600:
        message = message[:600] + "..."

    compressed_data = data.get("data")
    if isinstance(compressed_data, list) and len(compressed_data) > 5:
        compressed_data = compressed_data[:5]
    elif isinstance(compressed_data, dict):
        # Truncate long string values
        compressed_data = {
            k: (v[:200] + "..." if isinstance(v, str) and len(v) > 200 else v)
            for k, v in list(compressed_data.items())[:10]
        }

    return {
        "success": data.get("success", True),
        "message": message,
        "data": compressed_data,
    }


def _compress_generic(data: Dict) -> Dict:
    """Generic compression: keep message, minimize data."""
    message = data.get("message", "")
    if len(message) > 800:
        message = message[:800] + "..."

    return {
        "success": data.get("success", True),
        "message": message,
    }


def compress_old_tool_results(messages: List[Dict], keep_recent_turns: int = 2) -> List[Dict]:
    """Compress tool results from older turns in the message history.

    Tool results from turns older than keep_recent_turns are truncated to
    a brief summary, saving significant tokens in long conversations.

    This modifies messages IN PLACE for efficiency.
    """
    if len(messages) < keep_recent_turns * 3:  # Not enough turns to compress
        return messages

    # Find tool_result messages (they have role=user with list content)
    tool_result_indices = []
    for i, msg in enumerate(messages):
        content = msg.get("content", "")
        if isinstance(content, list) and any(
            isinstance(b, dict) and b.get("type") == "tool_result"
            for b in content
        ):
            tool_result_indices.append(i)

    # Keep the most recent N tool results intact
    old_indices = tool_result_indices[:-keep_recent_turns] if len(tool_result_indices) > keep_recent_turns else []

    compressed_count = 0
    for idx in old_indices:
        content = messages[idx].get("content", [])
        if not isinstance(content, list):
            continue

        new_content = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                old_text = block.get("content", "")
                if len(old_text) > MAX_OLD_TOOL_RESULT_CHARS:
                    # Truncate old tool result
                    try:
                        data = json.loads(old_text)
                        summary = data.get("message", "")[:200] if isinstance(data, dict) else old_text[:200]
                    except (json.JSONDecodeError, TypeError):
                        summary = old_text[:200]

                    block = {
                        "type": "tool_result",
                        "tool_use_id": block.get("tool_use_id", ""),
                        "content": json.dumps({"summary": summary}, ensure_ascii=False),
                    }
                    compressed_count += 1

            new_content.append(block)

        messages[idx]["content"] = new_content

    if compressed_count > 0:
        logger.info("Compressed %d old tool results to save tokens", compressed_count)

    return messages
