"""OpenClaw HTTP API Server — expose the agent system via REST.

Endpoints:
    POST /chat              → Send a message, get agent response
    POST /chat/stream       → Send a message, get SSE stream (future)
    GET  /agents            → List available agents
    POST /reset             → Reset conversation
    GET  /health            → Health check

Usage:
    python api.py                          # start server on port 18790
    OPENCLAW_PORT=8080 python api.py       # custom port

Environment:
    ANTHROPIC_API_KEY     — required
    BLUEWAVE_API_URL      — Bluewave backend URL
    BLUEWAVE_API_KEY      — Bluewave API key
    OPENCLAW_PORT         — server port (default: 18790)
    OPENCLAW_MODEL        — Claude model override
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from typing import Dict, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("openclaw.api")

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("Install dependencies: pip install fastapi uvicorn httpx anthropic")
    sys.exit(1)

from orchestrator import Orchestrator
from handler import BlueWaveHandler

# ── Config ────────────────────────────────────────────────────

PORT = int(os.environ.get("OPENCLAW_PORT", "18790"))

# ── Pydantic models ──────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    response: str
    session_id: str
    elapsed_seconds: float


# ── App ──────────────────────────────────────────────────────

app = FastAPI(
    title="OpenClaw Agent API",
    description="Multi-agent AI system for Bluewave Creative Operations",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session store: session_id -> Orchestrator instance
sessions = {}  # type: Dict[str, Orchestrator]
handler = None  # type: Optional[BlueWaveHandler]


def get_orchestrator(session_id: str = "default") -> Orchestrator:
    """Get or create an orchestrator for a session."""
    if session_id not in sessions:
        sessions[session_id] = Orchestrator(handler=handler)
        logger.info("New session created: %s", session_id)
    return sessions[session_id]


# ── Startup ──────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    global handler
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set! Agent will not work.")
        return

    try:
        handler = BlueWaveHandler()
        logger.info("BlueWaveHandler connected to %s", handler.api_url)
    except ValueError as e:
        logger.warning("BlueWaveHandler init failed: %s", e)
        logger.warning("Agent will work but tool calls will fail.")

    logger.info(
        "🌊 OpenClaw Agent API ready on port %d | model=%s",
        PORT, os.environ.get("OPENCLAW_MODEL", "claude-sonnet-4-20250514"),
    )


# ── Endpoints ────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "openclaw-agent",
        "handler_connected": handler is not None,
        "active_sessions": len(sessions),
        "model": os.environ.get("OPENCLAW_MODEL", "claude-sonnet-4-20250514"),
    }


@app.get("/agents")
async def list_agents():
    """List all available agents in the system."""
    orch = get_orchestrator("_meta")
    agents = [
        {
            "id": "bluewave-orchestrator",
            "name": "Wave",
            "emoji": "🌊",
            "role": "orchestrator",
            "description": orch.orchestrator_config.description,
        }
    ]
    for sid, config in orch.specialists.items():
        agents.append({
            "id": sid,
            "name": config.name,
            "emoji": config.emoji,
            "role": "specialist",
            "description": config.description,
            "tools_count": len(config.tool_names),
        })
    return {"agents": agents}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Send a message to the orchestrator and get a response."""
    if not req.message.strip():
        raise HTTPException(400, "Empty message")

    orch = get_orchestrator(req.session_id)
    t0 = time.time()

    try:
        response = await orch.chat(req.message)
    except Exception as e:
        logger.error("Chat error: %s", e, exc_info=True)
        raise HTTPException(500, "Agent error: %s" % str(e))

    elapsed = time.time() - t0
    logger.info(
        "Session %s | %.1fs | %s... -> %s...",
        req.session_id, elapsed,
        req.message[:50], response[:80],
    )

    return ChatResponse(
        response=response,
        session_id=req.session_id,
        elapsed_seconds=round(elapsed, 2),
    )


@app.post("/reset")
async def reset_session(session_id: str = "default"):
    """Reset a session's conversation history."""
    if session_id in sessions:
        sessions[session_id].reset()
        return {"status": "reset", "session_id": session_id}
    return {"status": "no_session", "session_id": session_id}


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session entirely."""
    if session_id in sessions:
        del sessions[session_id]
        return {"status": "deleted", "session_id": session_id}
    raise HTTPException(404, "Session not found")


@app.get("/sessions")
async def list_sessions():
    """List active sessions."""
    return {
        "sessions": [
            {
                "session_id": sid,
                "messages": len(orch.messages),
            }
            for sid, orch in sessions.items()
            if sid != "_meta"
        ]
    }


# ── Main ─────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
