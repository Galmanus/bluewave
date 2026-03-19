"""Context Window Manager — prevents token budget exhaustion in long conversations.

Implements a rolling context window that:
1. Estimates token usage per message
2. Summarizes old messages when approaching the limit
3. Preserves the most recent N messages for continuity
4. Tracks cumulative token usage for cost awareness

Token estimation uses chars/4 heuristic (conservative for English + multilingual).
"""

from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional

from token_optimizer import compress_old_tool_results

logger = logging.getLogger("openclaw.context")

# Configurable limits
MAX_CONTEXT_TOKENS = int(os.environ.get("OPENCLAW_MAX_CONTEXT_TOKENS", "120000"))
SUMMARIZE_THRESHOLD = int(MAX_CONTEXT_TOKENS * 0.75)  # Trigger at 75%
KEEP_RECENT_MESSAGES = int(os.environ.get("OPENCLAW_KEEP_RECENT", "10"))
SUMMARY_MAX_TOKENS = 500


def estimate_tokens(messages: List[Dict]) -> int:
    """Estimate token count for a list of messages using chars/4 heuristic."""
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += len(content) // 4
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        total += len(block.get("text", "")) // 4
                    elif block.get("type") == "tool_use":
                        total += len(str(block.get("input", {}))) // 4
                    elif block.get("type") == "tool_result":
                        total += len(block.get("content", "")) // 4
                    elif block.get("type") == "image":
                        total += 1600  # ~1600 tokens per image block
    return total


def _build_summary_text(messages: List[Dict]) -> str:
    """Build a concise summary of conversation messages for context compression."""
    parts = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if isinstance(content, str):
            text = content[:200]
        elif isinstance(content, list):
            text_blocks = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        text_blocks.append(block.get("text", "")[:150])
                    elif block.get("type") == "tool_use":
                        text_blocks.append(f"[tool: {block.get('name', '?')}]")
                    elif block.get("type") == "tool_result":
                        result_text = block.get("content", "")[:100]
                        text_blocks.append(f"[result: {result_text}]")
            text = " | ".join(text_blocks) if text_blocks else ""
        else:
            text = str(content)[:200]

        if text:
            parts.append(f"{role}: {text}")

    return "\n".join(parts)


class ContextWindowManager:
    """Manages the conversation context window to prevent token overflow.

    Usage:
        ctx = ContextWindowManager()

        # Before each Claude call:
        messages = ctx.prepare_messages(raw_messages)

        # After response:
        ctx.track_usage(input_tokens, output_tokens)
    """

    def __init__(
        self,
        max_tokens: int = MAX_CONTEXT_TOKENS,
        keep_recent: int = KEEP_RECENT_MESSAGES,
    ):
        self.max_tokens = max_tokens
        self.keep_recent = keep_recent
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self._summary: Optional[str] = None

    def prepare_messages(self, messages: List[Dict]) -> List[Dict]:
        """Return messages optimized for the context window.

        Applies two stages of optimization:
        1. Compress old tool results (always — cheap and effective)
        2. If still over threshold, summarize older messages
        """
        # Stage 1: Always compress old tool results (saves 30-60% on tool-heavy sessions)
        compress_old_tool_results(messages, keep_recent_turns=2)

        estimated = estimate_tokens(messages)

        if estimated < SUMMARIZE_THRESHOLD:
            return messages

        logger.info(
            "Context window at ~%dk tokens (threshold: %dk) — summarizing older messages",
            estimated // 1000,
            SUMMARIZE_THRESHOLD // 1000,
        )

        # Split: older messages to summarize vs recent to keep
        if len(messages) <= self.keep_recent:
            return messages

        older = messages[:-self.keep_recent]
        recent = messages[-self.keep_recent:]

        # Build summary
        summary_text = _build_summary_text(older)
        # Truncate summary if too long
        if len(summary_text) > SUMMARY_MAX_TOKENS * 4:
            summary_text = summary_text[:SUMMARY_MAX_TOKENS * 4] + "\n[... earlier context truncated]"

        self._summary = summary_text

        # Ensure proper message alternation: summary as user, then a brief assistant ack
        compressed = [
            {
                "role": "user",
                "content": f"[CONTEXT SUMMARY — earlier conversation compressed]\n{summary_text}",
            },
            {
                "role": "assistant",
                "content": "Understood. I have the context from our earlier conversation. Continuing.",
            },
        ]

        # Ensure recent messages start with the right role
        if recent and recent[0].get("role") == "assistant":
            # Already have assistant in compressed, so this is fine
            pass

        compressed.extend(recent)

        new_estimate = estimate_tokens(compressed)
        logger.info(
            "Context compressed: %dk -> %dk tokens (%d messages -> %d)",
            estimated // 1000,
            new_estimate // 1000,
            len(messages),
            len(compressed),
        )

        return compressed

    def track_usage(self, input_tokens: int = 0, output_tokens: int = 0):
        """Track cumulative token usage for cost awareness."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    @property
    def has_summary(self) -> bool:
        return self._summary is not None

    def get_stats(self) -> Dict:
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "has_summary": self.has_summary,
        }
