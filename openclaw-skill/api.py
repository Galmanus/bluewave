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
    from fastapi.responses import JSONResponse, StreamingResponse
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


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """Send a message and receive the response as a Server-Sent Events stream.

    Each SSE event has the format:
        data: {"type": "chunk"|"tool_start"|"tool_end"|"done"|"error", ...}

    Types:
        chunk      — partial text response: {"type": "chunk", "text": "..."}
        tool_start — agent is calling a tool: {"type": "tool_start", "tool": "..."}
        tool_end   — tool returned result: {"type": "tool_end", "tool": "..."}
        done       — final response complete: {"type": "done", "response": "...", "elapsed": 1.23}
        error      — error occurred: {"type": "error", "message": "..."}
    """
    if not req.message.strip():
        raise HTTPException(400, "Empty message")

    orch = get_orchestrator(req.session_id)

    async def event_generator():
        t0 = time.time()
        try:
            # Use the streaming-aware chat method
            response = await orch.chat_streaming(
                req.message,
                on_text_chunk=lambda chunk: None,  # chunks collected below
                on_tool_start=lambda name: None,
                on_tool_end=lambda name: None,
            )
        except AttributeError:
            # Fallback: orchestrator doesn't have streaming yet — use regular chat
            try:
                response = await orch.chat(req.message)
                # Send as one big chunk
                yield "data: %s\n\n" % json.dumps({"type": "chunk", "text": response})
                elapsed = time.time() - t0
                yield "data: %s\n\n" % json.dumps({
                    "type": "done",
                    "response": response,
                    "elapsed": round(elapsed, 2),
                    "session_id": req.session_id,
                })
                return
            except Exception as e:
                yield "data: %s\n\n" % json.dumps({"type": "error", "message": str(e)})
                return
        except Exception as e:
            yield "data: %s\n\n" % json.dumps({"type": "error", "message": str(e)})
            return

        elapsed = time.time() - t0
        yield "data: %s\n\n" % json.dumps({
            "type": "done",
            "response": response,
            "elapsed": round(elapsed, 2),
            "session_id": req.session_id,
        })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
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


# ── Brand Compliance Check (direct Vision, no orchestrator) ──

@app.post("/compliance-check")
async def compliance_check(request: Request):
    """Direct brand compliance analysis via Claude Vision.

    Bypasses orchestrator. Sends image + brand DNA to Haiku Vision.
    Cost: ~$0.005 per image.
    """
    import time as _time
    from brand_vision import analyze_brand_compliance

    body = await request.json()
    image_b64 = body.get("image_base64", "")
    media_type = body.get("media_type", "image/jpeg")

    if not image_b64 or len(image_b64) < 100:
        return {"response": "Invalid image data.", "elapsed_seconds": 0}

    t0 = _time.time()
    result = await analyze_brand_compliance(image_b64, media_type)
    elapsed = _time.time() - t0

    logger.info("Compliance check completed in %.1fs", elapsed)
    return {"response": result, "elapsed_seconds": elapsed}


# ── Brand Content Generation ─────────────────────────────────

@app.post("/generate-content")
async def generate_content_endpoint(request: Request):
    """Generate on-brand content using Brand DNA.

    Expects: {
        "content_type": "caption|stories|headline|cta|description|hashtags",
        "context": "what the content is about",
        "channel": "instagram_feed|instagram_stories|facebook|linkedin|tiktok|email|website",
        "language": "pt-BR",
        "variations": 1-5
    }
    """
    import time as _time
    from brand_content import generate_content

    body = await request.json()
    t0 = _time.time()

    result = await generate_content(
        content_type=body.get("content_type", "caption"),
        context=body.get("context", ""),
        channel=body.get("channel", "instagram_feed"),
        language=body.get("language", "pt-BR"),
        variations=min(body.get("variations", 1), 5),
    )

    elapsed = _time.time() - t0
    logger.info("Content generated in %.1fs (type=%s, channel=%s)",
                elapsed, body.get("content_type"), body.get("channel"))

    return {"content": result, "elapsed_seconds": elapsed}


# ── Brand Suite (10 high-revenue features) ───────────────────

@app.post("/brand/social-calendar")
async def social_calendar(request: Request):
    import time as _t; t=_t.time()
    from brand_suite import generate_social_calendar
    b = await request.json()
    r = await generate_social_calendar(b.get("weeks",4), b.get("posts_per_week",5), b.get("channels","instagram_feed,instagram_stories"), b.get("themes",""), b.get("language","pt-BR"))
    return {"content": r, "elapsed_seconds": _t.time()-t}

@app.post("/brand/repurpose")
async def repurpose(request: Request):
    import time as _t; t=_t.time()
    from brand_suite import repurpose_content
    b = await request.json()
    r = await repurpose_content(b.get("content",""), b.get("channel","instagram_feed"), b.get("language","pt-BR"))
    return {"content": r, "elapsed_seconds": _t.time()-t}

@app.post("/brand/ad-copy")
async def ad_copy(request: Request):
    import time as _t; t=_t.time()
    from brand_suite import generate_ad_copy
    b = await request.json()
    r = await generate_ad_copy(b.get("product",""), b.get("objective","conversions"), b.get("audience",""), b.get("variations",3), b.get("language","pt-BR"))
    return {"content": r, "elapsed_seconds": _t.time()-t}

@app.post("/brand/email-sequence")
async def email_seq(request: Request):
    import time as _t; t=_t.time()
    from brand_suite import generate_email_sequence
    b = await request.json()
    r = await generate_email_sequence(b.get("type","welcome"), b.get("count",5), b.get("product",""), b.get("language","pt-BR"))
    return {"content": r, "elapsed_seconds": _t.time()-t}

@app.post("/brand/product-descriptions")
async def prod_desc(request: Request):
    import time as _t; t=_t.time()
    from brand_suite import generate_product_descriptions
    b = await request.json()
    r = await generate_product_descriptions(b.get("products",[]), b.get("style","short"), b.get("language","pt-BR"))
    return {"content": r, "elapsed_seconds": _t.time()-t}

@app.post("/brand/hashtags")
async def hashtags(request: Request):
    import time as _t; t=_t.time()
    from brand_suite import research_hashtags
    b = await request.json()
    r = await research_hashtags(b.get("topic",""), b.get("count",15), b.get("language","pt-BR"))
    return {"content": r, "elapsed_seconds": _t.time()-t}

@app.post("/brand/competitor-audit")
async def comp_audit(request: Request):
    import time as _t; t=_t.time()
    from brand_suite import audit_competitor_content
    b = await request.json()
    r = await audit_competitor_content(b.get("competitor",""), b.get("description",""), b.get("language","pt-BR"))
    return {"content": r, "elapsed_seconds": _t.time()-t}

@app.post("/brand/report")
async def brand_report(request: Request):
    import time as _t; t=_t.time()
    from brand_suite import generate_brand_report
    b = await request.json()
    r = await generate_brand_report(b.get("period","monthly"), b.get("scores",[]), b.get("content_generated",0), b.get("language","pt-BR"))
    return {"content": r, "elapsed_seconds": _t.time()-t}


# ── Main ─────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
