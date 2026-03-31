"""Bluewave OpenClaw Skill Server.

Lightweight HTTP server that OpenClaw calls to execute tool functions.
Runs on port 18790 by default.

Endpoints:
  GET  /health                → { "status": "ok" }
  GET  /tools                 → tools.json manifest
  POST /execute               → { "tool": "...", "params": {...} } → ToolResult
  POST /hooks/bluewave        → Webhook receiver from Bluewave → formatted message
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import sys
from pathlib import Path
from typing import Optional, Union, Any

from handler import BlueWaveHandler, format_webhook_event
from skills_handler import get_all_skill_tools, execute_skill as exec_skill_tool, is_skill_tool

# Defer import — uvicorn will install these
try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
    import uvicorn
except ImportError:
    print("Install dependencies: pip install fastapi uvicorn httpx")
    sys.exit(1)

PORT = int(os.environ.get("BLUEWAVE_SKILL_PORT", "18790"))
WEBHOOK_SECRET = os.environ.get("OPENCLAW_HOOK_TOKEN", "")

app = FastAPI(title="Bluewave OpenClaw Skill", version="1.0.0")

# Load tools manifest
TOOLS_PATH = Path(__file__).parent / "tools.json"
CORE_TOOLS = json.loads(TOOLS_PATH.read_text()).get("tools", []) if TOOLS_PATH.exists() else []

# Load skill tools from skills_handler
SKILL_TOOLS = get_all_skill_tools()

# Combined tools manifest
TOOLS_MANIFEST = {
    "name": "bluewave",
    "version": "1.0.0",
    "description": "Bluewave AI Creative Operations + 260+ Specialized Research & Strategy Skills",
    "tools": CORE_TOOLS + SKILL_TOOLS
}

# Load agents manifest
AGENTS_PATH = Path(__file__).parent / "agents.json"
AGENTS_MANIFEST = json.loads(AGENTS_PATH.read_text()) if AGENTS_PATH.exists() else {}

# Initialize handler (will fail fast if no API key)
handler: Optional[BlueWaveHandler] = None


@app.on_event("startup")
async def startup():
    global handler
    try:
        handler = BlueWaveHandler()
        print(f"Bluewave skill connected to {handler.api_url}")
    except ValueError as e:
        print(f"WARNING: {e}")
        print("Skill will start but tool execution will fail until BLUEWAVE_API_KEY is set.")


# ── Health ─────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "skill": "bluewave",
        "connected": handler is not None,
        "api_url": handler.api_url if handler else None,
    }


# ── Tools Manifest ─────────────────────────────────────────────

@app.get("/tools")
async def get_tools():
    """Return the tools.json manifest for OpenClaw to discover available tools."""
    return TOOLS_MANIFEST


# ── Agents Manifest ───────────────────────────────────────────

@app.get("/agents")
async def get_agents():
    """Return the agents.json manifest for OpenClaw to discover available agents."""
    return AGENTS_MANIFEST


# ── Tool Execution ─────────────────────────────────────────────

@app.post("/execute")
async def execute_tool(request: Request):
    """Execute a tool call.

    Body: { "tool": "bluewave_list_assets", "params": { "status": "draft" } }
    """
    body = await request.json()
    tool_name = body.get("tool", "")
    params = body.get("params", {})

    if not tool_name:
        raise HTTPException(400, "Missing 'tool' field.")

    # 1. Check if it's a skill tool (e.g. web_search, unit_economics)
    if is_skill_tool(tool_name):
        result = await exec_skill_tool(tool_name, params)
        # Wrap in consistent format
        return {
            "success": result.get("success", False),
            "data": result.get("data"),
            "message": result.get("message", "No message")
        }

    # 2. Otherwise it's a core Bluewave tool
    if not handler:
        raise HTTPException(503, "Bluewave handler not initialized. Set BLUEWAVE_API_KEY.")

    result = await handler.execute(tool_name, params)
    return result.to_dict()


# ── Webhook Receiver ───────────────────────────────────────────

@app.post("/hooks/bluewave")
async def receive_webhook(request: Request):
    """Receive webhook events FROM Bluewave and format them for chat delivery.

    Validates HMAC-SHA256 signature if OPENCLAW_HOOK_TOKEN is set.
    Returns a formatted message that OpenClaw can deliver to chat.
    """
    body_bytes = await request.body()

    # Verify signature if secret is configured
    if WEBHOOK_SECRET:
        sig_header = request.headers.get("X-Webhook-Signature", "")
        expected = hmac.new(
            WEBHOOK_SECRET.encode(), body_bytes, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(sig_header, expected):
            raise HTTPException(401, "Invalid webhook signature")

    try:
        payload = json.loads(body_bytes)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON")

    event = payload.get("event", "unknown")
    data = payload.get("data", {})

    message = format_webhook_event(event, data)

    return {
        "message": message,
        "agentId": "bluewave",
        "deliver": True,
        "channel": "last",
    }


# ── Main ───────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
