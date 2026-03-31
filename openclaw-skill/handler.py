"""Bluewave OpenClaw Skill Handler.

Executes tool calls from the OpenClaw agent against the Bluewave REST API.
Reads BLUEWAVE_API_URL and BLUEWAVE_API_KEY from environment.

Usage:
    from handler import BlueWaveHandler
    handler = BlueWaveHandler()
    result = await handler.execute("bluewave_list_assets", {"status": "draft"})
"""

from __future__ import annotations

import json
import mimetypes
import os
from dataclasses import dataclass
from typing import Any, Optional

import httpx

BLUEWAVE_API_URL = os.environ.get("BLUEWAVE_API_URL", "http://localhost:8300/api/v1")
BLUEWAVE_API_KEY = os.environ.get("BLUEWAVE_API_KEY", "")
LANGSMITH_TRACE_HEADER = "X-Langsmith-Trace"

# Timeout for regular requests and uploads
TIMEOUT_DEFAULT = httpx.Timeout(30.0, connect=10.0)
TIMEOUT_UPLOAD = httpx.Timeout(120.0, connect=10.0)


@dataclass
class ToolResult:
    """Structured result from a tool execution."""
    success: bool
    data: Any
    message: str

    def to_dict(self) -> dict:
        return {"success": self.success, "data": self.data, "message": self.message}

    def to_chat(self) -> str:
        """Format result for chat display."""
        if not self.success:
            return f"Error: {self.message}"
        return self.message


class BlueWaveHandler:
    """Executes Bluewave tool calls via REST API."""

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        langsmith_run_id: Optional[str] = None,
    ):
        self.api_url = (api_url or BLUEWAVE_API_URL).rstrip("/")
        self.api_key = api_key or BLUEWAVE_API_KEY
        self.langsmith_run_id = langsmith_run_id
        if not self.api_key:
            raise ValueError(
                "BLUEWAVE_API_KEY is required. "
                "Set it in your environment or pass it to BlueWaveHandler()."
            )

    def _headers(self) -> dict[str, str]:
        headers = {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
        }
        if self.langsmith_run_id:
            headers[LANGSMITH_TRACE_HEADER] = self.langsmith_run_id
        return headers

    async def execute(self, tool_name: str, params: dict[str, Any]) -> ToolResult:
        """Dispatch a tool call to the appropriate handler."""
        dispatch = {
            # ── Existing tools ────────────────────────────────────
            "bluewave_list_assets": self._list_assets,
            "bluewave_get_asset": self._get_asset,
            "bluewave_upload_asset": self._upload_asset,
            "bluewave_update_asset": self._update_asset,
            "bluewave_delete_asset": self._delete_asset,
            "bluewave_submit_for_approval": self._submit_for_approval,
            "bluewave_approve_asset": self._approve_asset,
            "bluewave_reject_asset": self._reject_asset,
            "bluewave_regenerate_caption": self._regenerate_caption,
            "bluewave_regenerate_hashtags": self._regenerate_hashtags,
            "bluewave_check_compliance": self._check_compliance,
            "bluewave_ai_usage": self._ai_usage,
            "bluewave_list_team": self._list_team,
            "bluewave_get_profile": self._get_profile,
            "bluewave_invite_user": self._invite_user,
            "bluewave_get_brand_guidelines": self._get_brand_guidelines,
            # ── Enhanced tools — Asset Curator ────────────────────
            "bluewave_search_assets": self._search_assets,
            "bluewave_bulk_export": self._bulk_export,
            "bluewave_asset_variants": self._asset_variants,
            # ── Enhanced tools — Workflow Director ────────────────
            "bluewave_batch_approve": self._batch_approve,
            "bluewave_workflow_stats": self._workflow_stats,
            "bluewave_auto_approve_by_score": self._auto_approve_by_score,
            # ── Enhanced tools — Brand Guardian ───────────────────
            "bluewave_update_brand_guidelines": self._update_brand_guidelines,
            "bluewave_compliance_report": self._compliance_report,
            "bluewave_check_external_image": self._check_external_image,
            # ── Enhanced tools — Analytics Strategist ─────────────
            "bluewave_dashboard_metrics": self._dashboard_metrics,
            "bluewave_roi_report": self._roi_report,
            "bluewave_trend_analysis": self._trend_analysis,
            "bluewave_team_productivity": self._team_productivity,
            # ── Enhanced tools — Creative Strategist ──────────────
            "bluewave_generate_brief": self._generate_brief,
            "bluewave_caption_variants": self._caption_variants,
            "bluewave_translate_caption": self._translate_caption,
            "bluewave_content_calendar": self._content_calendar,
            "bluewave_schedule_post": self._schedule_post,
            # ── Enhanced tools — Ops Admin ────────────────────────
            "bluewave_remove_user": self._remove_user,
            "bluewave_update_user_role": self._update_user_role,
            "bluewave_billing_summary": self._billing_summary,
            "bluewave_create_api_key": self._create_api_key,
            "bluewave_audit_log": self._audit_log,
            "bluewave_storage_usage": self._storage_usage,
        }
        handler = dispatch.get(tool_name)
        if not handler:
            return ToolResult(False, None, f"Unknown tool: {tool_name}")
        try:
            return await handler(params)
        except httpx.HTTPStatusError as e:
            detail = ""
            try:
                body = e.response.json()
                detail = body.get("detail", "") if isinstance(body, dict) else str(body)
            except Exception:
                detail = e.response.text[:200]
            if e.response.status_code == 500:
                return ToolResult(False, None,
                    f"Backend error on {tool_name}. The feature may require data "
                    f"that doesn't exist yet (empty tenant). Detail: {detail or 'Internal Server Error'}")
            return ToolResult(False, None, f"API error {e.response.status_code}: {detail}")
        except httpx.ConnectError:
            return ToolResult(False, None, f"Cannot connect to Bluewave at {self.api_url}")
        except Exception as e:
            return ToolResult(False, None, f"Unexpected error: {e}")

    # ── Assets ─────────────────────────────────────────────────

    async def _list_assets(self, params: dict) -> ToolResult:
        query: dict[str, Any] = {
            "page": params.get("page", 1),
            "size": params.get("size", 10),
        }
        if params.get("status"):
            query["status"] = params["status"]

        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            r = await c.get(f"{self.api_url}/assets", headers=self._headers(), params=query)
            r.raise_for_status()

        data = r.json()
        items = data.get("items", [])
        total = data.get("total", 0)

        if not items:
            return ToolResult(True, data, "No assets found.")

        lines = [f"**{total} assets** (page {data.get('page', 1)}):"]
        for a in items:
            status_icon = {"draft": "📝", "pending_approval": "⏳", "approved": "✅"}.get(a["status"], "❓")
            caption = (a.get("caption") or "No caption")[:60]
            lines.append(f"{status_icon} `{a['id'][:8]}` — {caption} [{a['status']}]")

        return ToolResult(True, data, "\n".join(lines))

    async def _get_asset(self, params: dict) -> ToolResult:
        asset_id = params["asset_id"]
        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            r = await c.get(f"{self.api_url}/assets/{asset_id}", headers=self._headers())
            r.raise_for_status()

        a = r.json()
        hashtags = ", ".join(a.get("hashtags") or [])
        score = a.get("compliance_score")
        score_str = f"Compliance: {score}/100" if score is not None else "Compliance: not checked"

        msg = (
            f"**Asset** `{a['id'][:8]}`\n"
            f"**Status:** {a['status']}\n"
            f"**Caption:** {a.get('caption') or 'None'}\n"
            f"**Hashtags:** {hashtags or 'None'}\n"
            f"**Type:** {a['file_type']} ({_fmt_size(a['file_size'])})\n"
            f"**{score_str}**"
        )
        if a.get("rejection_comment"):
            msg += f"\n**Rejected:** {a['rejection_comment']}"

        return ToolResult(True, a, msg)

    async def _upload_asset(self, params: dict) -> ToolResult:
        file_url = params["file_url"]
        filename = params["filename"]

        # Download the file from the chat platform
        async with httpx.AsyncClient(timeout=TIMEOUT_UPLOAD) as c:
            dl = await c.get(file_url)
            dl.raise_for_status()
            content = dl.content

        content_type = (
            dl.headers.get("content-type", "").split(";")[0]
            or mimetypes.guess_type(filename)[0]
            or "application/octet-stream"
        )

        # Upload to Bluewave
        async with httpx.AsyncClient(timeout=TIMEOUT_UPLOAD) as c:
            r = await c.post(
                f"{self.api_url}/assets",
                headers={"X-API-Key": self.api_key},
                files={"file": (filename, content, content_type)},
            )
            r.raise_for_status()

        a = r.json()
        return ToolResult(
            True, a,
            f"Uploaded **{filename}** ({_fmt_size(len(content))})\n"
            f"Asset ID: `{a['id'][:8]}`\n"
            f"Status: {a['status']}\n"
            f"AI is generating caption and hashtags in the background — check back in a few seconds."
        )

    async def _update_asset(self, params: dict) -> ToolResult:
        asset_id = params["asset_id"]
        body: dict[str, Any] = {}
        if "caption" in params:
            body["caption"] = params["caption"]
        if "hashtags" in params:
            body["hashtags"] = params["hashtags"]

        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            r = await c.patch(
                f"{self.api_url}/assets/{asset_id}",
                headers={**self._headers(), "Content-Type": "application/json"},
                json=body,
            )
            r.raise_for_status()

        a = r.json()
        updated = ", ".join(body.keys())
        return ToolResult(True, a, f"Updated {updated} for asset `{a['id'][:8]}`.")

    async def _delete_asset(self, params: dict) -> ToolResult:
        asset_id = params["asset_id"]
        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            r = await c.delete(f"{self.api_url}/assets/{asset_id}", headers=self._headers())
            r.raise_for_status()

        return ToolResult(True, None, f"Asset `{asset_id[:8]}` deleted.")

    # ── Workflow ───────────────────────────────────────────────

    async def _submit_for_approval(self, params: dict) -> ToolResult:
        asset_id = params["asset_id"]
        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            r = await c.post(f"{self.api_url}/assets/{asset_id}/submit", headers=self._headers())
            r.raise_for_status()

        return ToolResult(True, r.json(), f"Asset `{asset_id[:8]}` submitted for approval. ⏳")

    async def _approve_asset(self, params: dict) -> ToolResult:
        asset_id = params["asset_id"]
        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            r = await c.post(f"{self.api_url}/assets/{asset_id}/approve", headers=self._headers())
            r.raise_for_status()

        return ToolResult(True, r.json(), f"Asset `{asset_id[:8]}` approved! ✅")

    async def _reject_asset(self, params: dict) -> ToolResult:
        asset_id = params["asset_id"]
        comment = params["comment"]
        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            r = await c.post(
                f"{self.api_url}/assets/{asset_id}/reject",
                headers={**self._headers(), "Content-Type": "application/json"},
                json={"comment": comment},
            )
            r.raise_for_status()

        return ToolResult(True, r.json(), f"Asset `{asset_id[:8]}` rejected: \"{comment}\"")

    # ── AI ─────────────────────────────────────────────────────

    async def _regenerate_caption(self, params: dict) -> ToolResult:
        asset_id = params["asset_id"]
        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            r = await c.post(f"{self.api_url}/ai/caption/{asset_id}", headers=self._headers())
            r.raise_for_status()

        a = r.json()
        return ToolResult(True, a, f"New caption for `{asset_id[:8]}`:\n\n> {a.get('caption', '—')}")

    async def _regenerate_hashtags(self, params: dict) -> ToolResult:
        asset_id = params["asset_id"]
        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            r = await c.post(f"{self.api_url}/ai/hashtags/{asset_id}", headers=self._headers())
            r.raise_for_status()

        a = r.json()
        tags = " ".join(a.get("hashtags") or [])
        return ToolResult(True, a, f"New hashtags for `{asset_id[:8]}`:\n{tags}")

    async def _check_compliance(self, params: dict) -> ToolResult:
        asset_id = params["asset_id"]
        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            r = await c.post(
                f"{self.api_url}/brand/check/{asset_id}",
                headers=self._headers(),
            )
            r.raise_for_status()

        data = r.json()
        score = data.get("score", "—")
        passed = "PASS ✅" if data.get("passed") else "FAIL ❌"
        summary = data.get("summary", "")

        lines = [f"**Compliance: {score}/100 — {passed}**"]
        if summary:
            lines.append(f"_{summary}_")
        for issue in data.get("issues", []):
            sev = {"error": "🔴", "warning": "🟡", "info": "🔵"}.get(issue.get("severity"), "•")
            lines.append(f"  {sev} [{issue.get('category')}] {issue.get('message')}")
            if issue.get("suggestion"):
                lines.append(f"    → {issue['suggestion']}")

        return ToolResult(True, data, "\n".join(lines))

    async def _ai_usage(self, params: dict) -> ToolResult:
        days = params.get("days", 30)
        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            r = await c.get(
                f"{self.api_url}/ai/usage",
                headers=self._headers(),
                params={"days": days},
            )
            r.raise_for_status()

        data = r.json()
        total = data.get("total_actions", 0)
        cost = data.get("total_cost_cents", 0)
        by_type = data.get("actions_by_type", {})

        lines = [f"**AI Usage (last {days} days)**", f"Total actions: **{total}**"]
        if by_type:
            for action, count in by_type.items():
                lines.append(f"  • {action}: {count}")
        lines.append(f"Total cost: **${cost:.2f}**")

        return ToolResult(True, data, "\n".join(lines))

    # ── Team ───────────────────────────────────────────────────

    async def _list_team(self, params: dict) -> ToolResult:
        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            r = await c.get(f"{self.api_url}/users", headers=self._headers())
            r.raise_for_status()

        users = r.json()
        if not users:
            return ToolResult(True, users, "No team members found.")

        lines = [f"**Team ({len(users)} members)**"]
        for u in users:
            role_icon = {"admin": "👑", "editor": "✏️", "viewer": "👁"}.get(u.get("role"), "•")
            lines.append(f"{role_icon} **{u['full_name']}** ({u['email']}) — {u['role']}")

        return ToolResult(True, users, "\n".join(lines))

    async def _get_profile(self, params: dict) -> ToolResult:
        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            r = await c.get(f"{self.api_url}/users/me", headers=self._headers())
            r.raise_for_status()

        u = r.json()
        return ToolResult(
            True, u,
            f"**{u['full_name']}** ({u['email']})\nRole: {u['role']}\nTenant: {u['tenant_id'][:8]}"
        )

    async def _invite_user(self, params: dict) -> ToolResult:
        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            r = await c.post(
                f"{self.api_url}/users",
                headers={**self._headers(), "Content-Type": "application/json"},
                json={
                    "email": params["email"],
                    "full_name": params["full_name"],
                    "role": params["role"],
                    "password": params["password"],
                },
            )
            r.raise_for_status()

        u = r.json()
        return ToolResult(
            True, u,
            f"Invited **{u['full_name']}** ({u['email']}) as **{u['role']}**."
        )

    # ── Brand ──────────────────────────────────────────────────

    async def _get_brand_guidelines(self, params: dict) -> ToolResult:
        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            r = await c.get(f"{self.api_url}/brand/guidelines", headers=self._headers())
            r.raise_for_status()

        data = r.json()
        if not data:
            return ToolResult(True, data, "No brand guidelines configured yet.")

        lines = ["**Brand Guidelines**"]
        if data.get("primary_colors"):
            lines.append(f"Primary colors: {', '.join(data['primary_colors'])}")
        if data.get("secondary_colors"):
            lines.append(f"Secondary colors: {', '.join(data['secondary_colors'])}")
        if data.get("fonts"):
            lines.append(f"Fonts: {', '.join(data['fonts'])}")
        if data.get("tone"):
            lines.append(f"Tone: {data['tone']}")
        if data.get("dos"):
            lines.append(f"Do: {'; '.join(data['dos'])}")
        if data.get("donts"):
            lines.append(f"Don't: {'; '.join(data['donts'])}")

        return ToolResult(True, data, "\n".join(lines))

    # ── Enhanced: Asset Curator ───────────────────────────────

    async def _search_assets(self, params: dict) -> ToolResult:
        query: dict[str, Any] = {"q": params["query"], "size": params.get("limit", 10)}
        if params.get("status"):
            query["status"] = params["status"]
        if params.get("file_type"):
            query["file_type"] = params["file_type"]

        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            r = await c.get(f"{self.api_url}/assets", headers=self._headers(), params=query)
            r.raise_for_status()

        data = r.json()
        items = data.get("items", [])
        total = data.get("total", 0)

        if not items:
            return ToolResult(True, data, f"No assets found matching \"{params['query']}\".")

        lines = [f"**{total} results** for \"{params['query']}\":"]
        for a in items:
            status_icon = {"draft": "📝", "pending_approval": "⏳", "approved": "✅"}.get(a["status"], "❓")
            caption = (a.get("caption") or "No caption")[:60]
            score = a.get("compliance_score")
            score_str = f", score {score}" if score is not None else ""
            lines.append(f"{status_icon} **{a.get('filename', a['id'][:8])}** — {caption} [{a['status']}{score_str}]")

        return ToolResult(True, data, "\n".join(lines))

    async def _bulk_export(self, params: dict) -> ToolResult:
        asset_ids = params["asset_ids"]
        async with httpx.AsyncClient(timeout=TIMEOUT_UPLOAD) as c:
            r = await c.post(
                f"{self.api_url}/assets/export",
                headers={**self._headers(), "Content-Type": "application/json"},
                json={"asset_ids": asset_ids},
            )
            r.raise_for_status()

        data = r.json()
        url = data.get("download_url", "")
        return ToolResult(True, data, f"Export ready! **{len(asset_ids)} assets** packaged.\nDownload: {url}")

    async def _asset_variants(self, params: dict) -> ToolResult:
        asset_id = params["asset_id"]
        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            r = await c.get(f"{self.api_url}/assets/{asset_id}/variants", headers=self._headers())
            r.raise_for_status()

        variants = r.json()
        if not variants:
            return ToolResult(True, variants, "No resize variants found for this asset.")

        lines = [f"**{len(variants)} variants:**"]
        for v in variants:
            lines.append(f"  • {v.get('label', v.get('name', '?'))} — {v.get('width', '?')}x{v.get('height', '?')} ({_fmt_size(v.get('file_size', 0))})")

        return ToolResult(True, variants, "\n".join(lines))

    # ── Enhanced: Workflow Director ───────────────────────────

    async def _batch_approve(self, params: dict) -> ToolResult:
        asset_ids = params["asset_ids"]
        comment = params.get("comment", "")
        approved = []
        failed = []

        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            for aid in asset_ids:
                try:
                    body = {"comment": comment} if comment else {}
                    r = await c.post(
                        f"{self.api_url}/assets/{aid}/approve",
                        headers={**self._headers(), "Content-Type": "application/json"},
                        json=body,
                    )
                    r.raise_for_status()
                    approved.append(aid)
                except Exception:
                    failed.append(aid)

        lines = [f"**Batch approve: {len(approved)}/{len(asset_ids)} succeeded**"]
        if approved:
            lines.append(f"✅ Approved: {len(approved)} assets")
        if failed:
            lines.append(f"❌ Failed: {len(failed)} assets")

        return ToolResult(True, {"approved": approved, "failed": failed}, "\n".join(lines))

    async def _workflow_stats(self, params: dict) -> ToolResult:
        days = params.get("days", 30)
        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            # Use overview endpoint + asset counts for workflow stats
            r = await c.get(
                f"{self.api_url}/analytics/overview",
                headers=self._headers(),
                params={"days": days},
            )
            r.raise_for_status()

        data = r.json()
        lines = [f"**Workflow Stats (last {days} days)**"]

        if "pending_count" in data:
            lines.append(f"📋 Pending: **{data['pending_count']}** assets")
        if "avg_approval_hours" in data:
            lines.append(f"⏱ Avg approval time: **{data['avg_approval_hours']:.1f}h**")
        if "approval_rate" in data:
            lines.append(f"✅ First-submission approval rate: **{data['approval_rate']:.0f}%**")
        if "rejection_rate" in data:
            lines.append(f"❌ Rejection rate: **{data['rejection_rate']:.0f}%**")
        if "by_status" in data:
            for status, count in data["by_status"].items():
                lines.append(f"  • {status}: {count}")

        return ToolResult(True, data, "\n".join(lines))

    async def _auto_approve_by_score(self, params: dict) -> ToolResult:
        min_score = params.get("min_score", 90)

        # Step 1: list pending assets
        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            r = await c.get(
                f"{self.api_url}/assets",
                headers=self._headers(),
                params={"status": "pending_approval", "size": 100},
            )
            r.raise_for_status()

        items = r.json().get("items", [])
        eligible = [a for a in items if (a.get("compliance_score") or 0) >= min_score]

        if not eligible:
            return ToolResult(True, {"approved": []}, f"No pending assets with compliance score >= {min_score}.")

        # Step 2: approve each eligible asset
        approved = []
        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            for a in eligible:
                try:
                    r = await c.post(
                        f"{self.api_url}/assets/{a['id']}/approve",
                        headers=self._headers(),
                    )
                    r.raise_for_status()
                    approved.append(a)
                except Exception:
                    pass

        skipped = len(items) - len(eligible)
        lines = [
            f"**Auto-approve (score >= {min_score}): {len(approved)}/{len(items)} assets**",
            f"✅ Approved: {len(approved)}",
        ]
        if skipped:
            lines.append(f"⏭ Skipped (score < {min_score}): {skipped}")

        return ToolResult(True, {"approved": [a["id"] for a in approved], "total_pending": len(items)}, "\n".join(lines))

    # ── Enhanced: Brand Guardian ──────────────────────────────

    async def _update_brand_guidelines(self, params: dict) -> ToolResult:
        body: dict[str, Any] = {}
        for key in ("colors", "fonts", "tone", "dos", "donts", "custom_rules"):
            if key in params:
                body[key] = params[key]

        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            r = await c.put(
                f"{self.api_url}/brand/guidelines",
                headers={**self._headers(), "Content-Type": "application/json"},
                json=body,
            )
            r.raise_for_status()

        updated = ", ".join(body.keys())
        return ToolResult(True, r.json(), f"Brand guidelines updated: {updated}.")

    async def _compliance_report(self, params: dict) -> ToolResult:
        days = params.get("days", 30)
        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            # Use AI quality endpoint for compliance stats
            r = await c.get(
                f"{self.api_url}/analytics/ai-quality",
                headers=self._headers(),
                params={"days": days},
            )
            r.raise_for_status()

        data = r.json()
        lines = [f"**Compliance Report (last {days} days)**"]

        if "avg_score" in data:
            lines.append(f"📊 Average score: **{data['avg_score']:.0f}/100**")
        if "pass_rate" in data:
            lines.append(f"✅ Pass rate: **{data['pass_rate']:.0f}%**")
        if "total_checks" in data:
            lines.append(f"🔍 Total checks: **{data['total_checks']}**")
        if "top_issues" in data:
            lines.append("**Top issues:**")
            for issue in data["top_issues"][:5]:
                lines.append(f"  • {issue.get('category', '?')}: {issue.get('count', '?')} occurrences")

        return ToolResult(True, data, "\n".join(lines))

    async def _check_external_image(self, params: dict) -> ToolResult:
        body: dict[str, Any] = {"image_url": params["image_url"]}
        if params.get("check_types"):
            body["check_types"] = params["check_types"]

        async with httpx.AsyncClient(timeout=TIMEOUT_UPLOAD) as c:
            # External image check not available yet — use brand check endpoint
            r = await c.post(
                f"{self.api_url}/brand/check-url",
                headers={**self._headers(), "Content-Type": "application/json"},
                json=body,
            )
            r.raise_for_status()

        data = r.json()
        score = data.get("score", "—")
        passed = "PASS ✅" if data.get("passed") else "FAIL ❌"

        lines = [f"**External image compliance: {score}/100 — {passed}**"]
        if data.get("summary"):
            lines.append(f"_{data['summary']}_")
        for issue in data.get("issues", []):
            sev = {"error": "🔴", "warning": "🟡", "info": "🔵"}.get(issue.get("severity"), "•")
            lines.append(f"  {sev} [{issue.get('category')}] {issue.get('message')}")
            if issue.get("suggestion"):
                lines.append(f"    → {issue['suggestion']}")

        return ToolResult(True, data, "\n".join(lines))

    # ── Enhanced: Analytics Strategist ────────────────────────

    async def _dashboard_metrics(self, params: dict) -> ToolResult:
        days = params.get("days", 30)
        query: dict[str, Any] = {"days": days}
        if params.get("compare"):
            query["compare"] = "true"

        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            r = await c.get(
                f"{self.api_url}/analytics/overview",
                headers=self._headers(),
                params=query,
            )
            r.raise_for_status()

        data = r.json()
        lines = [f"**Dashboard (last {days} days)**"]

        for section in ("volume", "speed", "efficiency", "cost"):
            if section in data:
                s = data[section]
                lines.append(f"\n**{section.title()}**")
                for key, val in s.items():
                    lines.append(f"  • {key}: {val}")

        return ToolResult(True, data, "\n".join(lines))

    async def _roi_report(self, params: dict) -> ToolResult:
        hourly_rate = params.get("hourly_rate", 50)
        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            r = await c.get(
                f"{self.api_url}/analytics/roi",
                headers=self._headers(),
                params={"hourly_rate": hourly_rate},
            )
            r.raise_for_status()

        data = r.json()
        lines = [f"**ROI Report** (@ ${hourly_rate}/h)"]

        if "hours_saved" in data:
            lines.append(f"⏱ Hours saved: **{data['hours_saved']:.1f}h**")
        if "value_generated" in data:
            lines.append(f"💰 Value: **${data['value_generated']:,.2f}**")
        if "platform_cost" in data:
            lines.append(f"💳 Platform cost: **${data['platform_cost']:,.2f}**")
        if "roi_percentage" in data:
            lines.append(f"📈 ROI: **{data['roi_percentage']:.0f}%**")

        return ToolResult(True, data, "\n".join(lines))

    async def _trend_analysis(self, params: dict) -> ToolResult:
        metric = params["metric"]
        days = params.get("days", 90)
        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            r = await c.get(
                f"{self.api_url}/analytics/trends",
                headers=self._headers(),
                params={"metric": metric, "days": days},
            )
            r.raise_for_status()

        data = r.json()
        lines = [f"**Trend Analysis: {metric}** (last {days} days)"]

        if "trend" in data:
            lines.append(f"📈 Trend: **{data['trend']}**")
        if "summary" in data:
            lines.append(data["summary"])
        if "data_points" in data:
            lines.append(f"Data points: {len(data['data_points'])}")

        return ToolResult(True, data, "\n".join(lines))

    async def _team_productivity(self, params: dict) -> ToolResult:
        days = params.get("days", 30)
        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            r = await c.get(
                f"{self.api_url}/analytics/team",
                headers=self._headers(),
                params={"days": days},
            )
            r.raise_for_status()

        data = r.json()
        members = data if isinstance(data, list) else data.get("members", [])

        if not members:
            return ToolResult(True, data, "No team productivity data available.")

        lines = [f"**Team Productivity (last {days} days)**"]
        for m in members:
            name = m.get("full_name", "Unknown")
            uploads = m.get("uploads", 0)
            approvals = m.get("approvals", 0)
            lines.append(f"  • **{name}** — {uploads} uploads, {approvals} approvals")

        return ToolResult(True, data, "\n".join(lines))

    # ── Enhanced: Creative Strategist ─────────────────────────

    async def _generate_brief(self, params: dict) -> ToolResult:
        body: dict[str, Any] = {"prompt": params["prompt"]}
        if params.get("channels"):
            body["channels"] = params["channels"]
        if params.get("tone"):
            body["tone"] = params["tone"]

        async with httpx.AsyncClient(timeout=TIMEOUT_UPLOAD) as c:
            r = await c.post(
                f"{self.api_url}/briefs",
                headers={**self._headers(), "Content-Type": "application/json"},
                json=body,
            )
            r.raise_for_status()

        data = r.json()
        brief = data.get("brief", data.get("content", ""))
        return ToolResult(True, data, f"**Creative Brief**\n\n{brief}")

    async def _caption_variants(self, params: dict) -> ToolResult:
        asset_id = params["asset_id"]
        body: dict[str, Any] = {}
        if params.get("tones"):
            body["tones"] = params["tones"]

        async with httpx.AsyncClient(timeout=TIMEOUT_UPLOAD) as c:
            r = await c.post(
                f"{self.api_url}/ai/caption/{asset_id}/translate",
                headers={**self._headers(), "Content-Type": "application/json"},
                json={"languages": ["professional", "casual", "storytelling"]},
            )
            r.raise_for_status()

        data = r.json()
        variants = data.get("variants", [])

        if not variants:
            return ToolResult(True, data, "No caption variants generated.")

        lines = [f"**{len(variants)} caption variants:**"]
        for i, v in enumerate(variants, 1):
            tone = v.get("tone", f"variant {i}")
            caption = v.get("caption", "")
            lines.append(f"\n**{i}. {tone.title()}**\n> {caption}")

        return ToolResult(True, data, "\n".join(lines))

    async def _translate_caption(self, params: dict) -> ToolResult:
        asset_id = params["asset_id"]
        languages = params["languages"]

        async with httpx.AsyncClient(timeout=TIMEOUT_UPLOAD) as c:
            r = await c.post(
                f"{self.api_url}/ai/caption/{asset_id}/translate",
                headers={**self._headers(), "Content-Type": "application/json"},
                json={"languages": languages},
            )
            r.raise_for_status()

        data = r.json()
        translations = data.get("translations", data)

        lines = ["**Translations:**"]
        if isinstance(translations, dict):
            for lang, text in translations.items():
                lines.append(f"  **{lang.upper()}:** {text}")
        elif isinstance(translations, list):
            for t in translations:
                lines.append(f"  **{t.get('language', '?').upper()}:** {t.get('caption', '')}")

        return ToolResult(True, data, "\n".join(lines))

    async def _content_calendar(self, params: dict) -> ToolResult:
        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            r = await c.get(
                f"{self.api_url}/calendar",
                headers=self._headers(),
                params={"start": params["start"], "end": params["end"]},
            )
            r.raise_for_status()

        data = r.json()
        events = data if isinstance(data, list) else data.get("events", [])

        if not events:
            return ToolResult(True, data, f"No scheduled posts from {params['start']} to {params['end']}.")

        lines = [f"**Content Calendar** ({params['start']} → {params['end']})"]
        for e in events:
            dt = e.get("scheduled_at", "?")[:16]
            channel = e.get("channel", "?")
            caption = (e.get("caption") or "No caption")[:40]
            lines.append(f"  📅 {dt} — **{channel}** — {caption}")

        return ToolResult(True, data, "\n".join(lines))

    async def _schedule_post(self, params: dict) -> ToolResult:
        body: dict[str, Any] = {
            "asset_id": params["asset_id"],
            "scheduled_at": params["scheduled_at"],
            "channel": params["channel"],
        }
        if params.get("caption_override"):
            body["caption_override"] = params["caption_override"]

        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            r = await c.post(
                f"{self.api_url}/calendar",
                headers={**self._headers(), "Content-Type": "application/json"},
                json=body,
            )
            r.raise_for_status()

        data = r.json()
        return ToolResult(
            True, data,
            f"Post scheduled! 📅\n"
            f"Channel: **{params['channel']}**\n"
            f"Time: {params['scheduled_at']}"
        )

    # ── Enhanced: Ops Admin ───────────────────────────────────

    async def _remove_user(self, params: dict) -> ToolResult:
        user_id = params["user_id"]
        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            r = await c.delete(f"{self.api_url}/users/{user_id}", headers=self._headers())
            r.raise_for_status()

        return ToolResult(True, None, f"User removed from the team.")

    async def _update_user_role(self, params: dict) -> ToolResult:
        user_id = params["user_id"]
        new_role = params["new_role"]
        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            r = await c.patch(
                f"{self.api_url}/users/{user_id}",
                headers={**self._headers(), "Content-Type": "application/json"},
                json={"role": new_role},
            )
            r.raise_for_status()

        u = r.json()
        name = u.get("full_name", user_id[:8])
        return ToolResult(True, u, f"**{name}** role updated to **{new_role}**.")

    async def _billing_summary(self, params: dict) -> ToolResult:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
                r = await c.get(f"{self.api_url}/billing/plan", headers=self._headers())
                r.raise_for_status()

            data = r.json()
            lines = ["**Billing Summary**"]

            if "plan" in data:
                lines.append(f"Plan: **{data['plan']}**")
            if "seats_used" in data and "seats_total" in data:
                lines.append(f"Seats: **{data['seats_used']}/{data['seats_total']}**")
            if "monthly_cost" in data:
                lines.append(f"Monthly cost: **${data['monthly_cost']:,.2f}**")
            if "ai_cost" in data:
                lines.append(f"AI usage cost: **${data['ai_cost']:,.2f}**")
            if "next_billing" in data:
                lines.append(f"Next billing: {data['next_billing']}")

            return ToolResult(True, data, "\n".join(lines))
        except Exception:
            # Fallback: get usage from billing/usage endpoint
            try:
                async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
                    r = await c.get(f"{self.api_url}/billing/usage", headers=self._headers())
                    r.raise_for_status()
                data = r.json()
                return ToolResult(True, data, f"**Billing Usage**\n{json.dumps(data, indent=2, default=str)[:500]}")
            except Exception:
                return ToolResult(True, {"plan": "free", "note": "Billing service unavailable"},
                    "**Billing:** Free tier (billing service temporarily unavailable)")

    async def _create_api_key(self, params: dict) -> ToolResult:
        body: dict[str, Any] = {"name": params["name"]}
        if params.get("permissions"):
            body["permissions"] = params["permissions"]

        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            r = await c.post(
                f"{self.api_url}/api-keys",
                headers={**self._headers(), "Content-Type": "application/json"},
                json=body,
            )
            r.raise_for_status()

        data = r.json()
        key = data.get("key", data.get("api_key", ""))
        return ToolResult(
            True, data,
            f"API key created: **{params['name']}**\n"
            f"Key: `{key}`\n"
            f"⚠️ Save this key — it won't be shown again."
        )

    async def _audit_log(self, params: dict) -> ToolResult:
        query: dict[str, Any] = {"days": params.get("days", 7)}
        if params.get("user_id"):
            query["user_id"] = params["user_id"]
        if params.get("action"):
            query["action"] = params["action"]

        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            r = await c.get(f"{self.api_url}/audit-logs", headers=self._headers(), params=query)
            r.raise_for_status()

        data = r.json()
        entries = data if isinstance(data, list) else data.get("entries", [])

        if not entries:
            return ToolResult(True, data, "No audit log entries found.")

        lines = [f"**Audit Log** (last {query['days']} days, {len(entries)} entries)"]
        for e in entries[:20]:
            ts = e.get("timestamp", "?")[:16]
            user = e.get("user_name", e.get("user_id", "?")[:8])
            action = e.get("action", "?")
            target = e.get("target", "")
            lines.append(f"  {ts} — **{user}** {action} {target}")

        if len(entries) > 20:
            lines.append(f"  ... and {len(entries) - 20} more entries")

        return ToolResult(True, data, "\n".join(lines))

    async def _storage_usage(self, params: dict) -> ToolResult:
        async with httpx.AsyncClient(timeout=TIMEOUT_DEFAULT) as c:
            r = await c.get(f"{self.api_url}/billing/usage", headers=self._headers())
            r.raise_for_status()

        data = r.json()
        lines = ["**Storage Usage**"]

        if "total_bytes" in data:
            lines.append(f"📦 Total: **{_fmt_size(data['total_bytes'])}**")
        if "by_type" in data:
            lines.append("By type:")
            for ftype, size in data["by_type"].items():
                lines.append(f"  • {ftype}: {_fmt_size(size)}")
        if "asset_count" in data:
            lines.append(f"📁 Total assets: **{data['asset_count']}**")

        return ToolResult(True, data, "\n".join(lines))


# ── Helpers ────────────────────────────────────────────────────

def _fmt_size(b: int) -> str:
    if b < 1024:
        return f"{b} B"
    if b < 1024 * 1024:
        return f"{b / 1024:.1f} KB"
    return f"{b / (1024 * 1024):.1f} MB"


# ── Webhook Event Formatter ───────────────────────────────────

def format_webhook_event(event: str, data: dict) -> str:
    """Format a Bluewave webhook event into a human-readable chat message.

    Used by OpenClaw's hook mapping to deliver notifications to chat channels.
    """
    formatters = {
        "asset.uploaded": lambda d: (
            f"📤 **New asset uploaded**\n"
            f"File: {d.get('file_type', 'unknown')} ({_fmt_size(d.get('file_size', 0))})\n"
            f"Uploaded by: {d.get('uploaded_by', 'unknown')}\n"
            f"AI is generating caption and hashtags..."
        ),
        "asset.submitted": lambda d: (
            f"📋 **Asset submitted for approval**\n"
            f"Caption: _{d.get('caption', 'None')}_\n"
            f"ID: `{str(d.get('id', ''))[:8]}`"
        ),
        "asset.approved": lambda d: (
            f"✅ **Asset approved!**\n"
            f"Caption: _{d.get('caption', 'None')}_\n"
            f"ID: `{str(d.get('id', ''))[:8]}`"
        ),
        "asset.rejected": lambda d: (
            f"❌ **Asset rejected**\n"
            f"Reason: {d.get('rejection_comment', 'No comment')}\n"
            f"ID: `{str(d.get('id', ''))[:8]}`"
        ),
        "ai.completed": lambda d: (
            f"🤖 **AI analysis complete**\n"
            f"Caption: _{d.get('caption', '')}_\n"
            f"Hashtags: {' '.join(d.get('hashtags', []))}"
        ),
        "user.invited": lambda d: (
            f"👋 **New team member**\n"
            f"{d.get('full_name', 'Unknown')} ({d.get('email', '')}) joined as {d.get('role', 'viewer')}"
        ),
        "user.removed": lambda d: (
            f"🚪 **Team member removed**\n"
            f"{d.get('full_name', 'Unknown')} ({d.get('email', '')}) has been removed"
        ),
    }

    formatter = formatters.get(event)
    if formatter:
        return formatter(data)
    return f"📡 **Bluewave event:** {event}\n```json\n{json.dumps(data, indent=2, default=str)[:500]}\n```"
