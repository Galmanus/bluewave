"""Batch AI Service — 50% cost reduction for non-real-time AI operations.

Uses Anthropic's Message Batches API for operations that can tolerate
up to 24h latency. Ideal for:
- Bulk compliance checks (e.g., re-check all assets after guideline change)
- Batch caption generation for newly uploaded assets
- Mass hashtag regeneration
- Bulk content brief generation

Cost: 50% of standard API pricing.
Latency: Up to 24h (typically 1-4h).

Usage:
    from app.services.batch_ai import BatchAIService

    batch = BatchAIService()
    batch_id = await batch.submit_compliance_checks(asset_ids, guidelines)
    # Poll later:
    results = await batch.get_results(batch_id)
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any

import anthropic

from app.core.config import settings
from app.core.prompt_safety import sanitize_for_prompt
from app.prompts import load_prompt

logger = logging.getLogger("bluewave.batch_ai")


class BatchAIService:
    """Handles batch AI operations via Anthropic Message Batches API."""

    def __init__(self):
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY required for batch operations")
        self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = settings.AI_MODEL

    async def submit_caption_batch(
        self,
        assets: list[dict],
    ) -> str:
        """Submit a batch of caption generation requests.

        Args:
            assets: list of {"id": str, "filename": str, "file_type": str}

        Returns:
            batch_id for polling results
        """
        system_prompt = load_prompt("caption_system")

        requests = []
        for asset in assets:
            safe_name = sanitize_for_prompt(asset["filename"], max_length=200)
            safe_type = sanitize_for_prompt(asset["file_type"], max_length=50)
            media_kind = "video" if asset["file_type"].startswith("video/") else "image"

            requests.append({
                "custom_id": f"caption_{asset['id']}",
                "params": {
                    "model": self._model,
                    "max_tokens": 300,
                    "system": system_prompt,
                    "messages": [
                        {
                            "role": "user",
                            "content": f"Generate a caption for a {media_kind} asset.\n<filename>{safe_name}</filename>\n<file_type>{safe_type}</file_type>",
                        }
                    ],
                },
            })

        batch = await self._client.messages.batches.create(requests=requests)
        logger.info("Caption batch submitted: %s (%d items)", batch.id, len(requests))
        return batch.id

    async def submit_compliance_batch(
        self,
        assets: list[dict],
        guidelines_text: str,
    ) -> str:
        """Submit a batch of compliance checks.

        Args:
            assets: list of {"id": str, "caption": str, "hashtags": list[str]}
            guidelines_text: pre-built guidelines prompt

        Returns:
            batch_id for polling results
        """
        requests = []
        for asset in assets:
            asset_info = f"Caption: \"{asset.get('caption', 'No caption')}\""
            if asset.get("hashtags"):
                asset_info += f"\nHashtags: {', '.join(asset['hashtags'])}"

            requests.append({
                "custom_id": f"compliance_{asset['id']}",
                "params": {
                    "model": self._model,
                    "max_tokens": 1000,
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                "Analyze this media asset for brand compliance.\n\n"
                                f"BRAND GUIDELINES:\n{guidelines_text}\n\n"
                                f"ASSET METADATA:\n{asset_info}\n\n"
                                "Score 0-100. Use the compliance_result tool."
                            ),
                        }
                    ],
                    "tools": [
                        {
                            "name": "compliance_result",
                            "description": "Return brand compliance analysis.",
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "score": {"type": "integer"},
                                    "summary": {"type": "string"},
                                    "issues": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "severity": {"type": "string", "enum": ["error", "warning", "info"]},
                                                "category": {"type": "string"},
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
                    ],
                    "tool_choice": {"type": "tool", "name": "compliance_result"},
                },
            })

        batch = await self._client.messages.batches.create(requests=requests)
        logger.info("Compliance batch submitted: %s (%d items)", batch.id, len(requests))
        return batch.id

    async def submit_hashtag_batch(
        self,
        assets: list[dict],
    ) -> str:
        """Submit a batch of hashtag generation requests."""
        system_prompt = load_prompt("hashtags_system")

        requests = []
        for asset in assets:
            safe_name = sanitize_for_prompt(asset["filename"], max_length=200)
            media_kind = "video" if asset.get("file_type", "").startswith("video/") else "image"

            requests.append({
                "custom_id": f"hashtags_{asset['id']}",
                "params": {
                    "model": self._model,
                    "max_tokens": 200,
                    "system": system_prompt,
                    "messages": [
                        {
                            "role": "user",
                            "content": f"Generate hashtags for a {media_kind} asset.\n<filename>{safe_name}</filename>",
                        }
                    ],
                },
            })

        batch = await self._client.messages.batches.create(requests=requests)
        logger.info("Hashtag batch submitted: %s (%d items)", batch.id, len(requests))
        return batch.id

    async def get_batch_status(self, batch_id: str) -> dict:
        """Check the status of a batch."""
        batch = await self._client.messages.batches.retrieve(batch_id)
        return {
            "id": batch.id,
            "status": batch.processing_status,
            "created_at": batch.created_at.isoformat() if batch.created_at else None,
            "counts": {
                "processing": batch.request_counts.processing,
                "succeeded": batch.request_counts.succeeded,
                "errored": batch.request_counts.errored,
                "canceled": batch.request_counts.canceled,
                "expired": batch.request_counts.expired,
            },
        }

    async def get_batch_results(self, batch_id: str) -> list[dict]:
        """Retrieve results from a completed batch."""
        results = []
        async for entry in self._client.messages.batches.results(batch_id):
            custom_id = entry.custom_id
            if entry.result.type == "succeeded":
                message = entry.result.message
                # Extract text or tool_use result
                text = ""
                tool_result = None
                for block in message.content:
                    if block.type == "text":
                        text = block.text
                    elif block.type == "tool_use":
                        tool_result = block.input

                results.append({
                    "custom_id": custom_id,
                    "success": True,
                    "text": text,
                    "tool_result": tool_result,
                    "usage": {
                        "input_tokens": message.usage.input_tokens,
                        "output_tokens": message.usage.output_tokens,
                    },
                })
            else:
                results.append({
                    "custom_id": custom_id,
                    "success": False,
                    "error": str(entry.result),
                })

        logger.info("Batch %s: %d results retrieved", batch_id, len(results))
        return results

    async def cancel_batch(self, batch_id: str) -> dict:
        """Cancel a running batch."""
        batch = await self._client.messages.batches.cancel(batch_id)
        return {"id": batch.id, "status": batch.processing_status}
