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

# ── API Key Tiers (for paid access) ──────────────────────────
#
# Free tier: 10 requests/day, Haiku only, no PUT/OSINT/agent-factory
# Pro tier:  1000 requests/day, Sonnet, full tools
# Enterprise: unlimited, Opus available, priority support
#
# Keys are set via environment or stored in a JSON file.
# Revenue from paid API access is 100% Manuel's when running
# outside Ialum infrastructure (clause 5.5b).

API_KEYS_FILE = os.path.join(os.path.dirname(__file__), "memory", "api_keys.json")

_API_KEYS = {}  # loaded at startup

def _load_api_keys():
    """Load API keys from file or environment."""
    global _API_KEYS
    # Built-in keys from environment
    env_keys = os.environ.get("WAVE_API_KEYS", "")
    if env_keys:
        try:
            _API_KEYS = json.loads(env_keys)
        except json.JSONDecodeError:
            pass

    # File-based keys
    if os.path.exists(API_KEYS_FILE):
        try:
            with open(API_KEYS_FILE, "r") as f:
                file_keys = json.loads(f.read())
                _API_KEYS.update(file_keys)
        except Exception:
            pass

    # Default demo key (always available, rate limited)
    _API_KEYS.setdefault("wave_demo_2026", {
        "owner": "demo",
        "tier": "free",
        "daily_limit": 10,
        "models": ["claude-haiku-4-5-20251001"],
        "tools_blocked": ["dork_contacts", "dork_pain_signals", "create_agent_soul",
                          "deploy_agent", "midas_read_file", "midas_write_file",
                          "gmail_send", "starknet_deploy_contracts"],
    })

    # Pro key template (set WAVE_PRO_KEY env var to activate)
    pro_key = os.environ.get("WAVE_PRO_KEY", "")
    if pro_key:
        _API_KEYS[pro_key] = {
            "owner": "pro_customer",
            "tier": "pro",
            "daily_limit": 1000,
            "models": ["claude-haiku-4-5-20251001", "claude-sonnet-4-20250514"],
            "tools_blocked": ["create_agent_soul", "deploy_agent",
                              "midas_write_file", "starknet_deploy_contracts"],
        }


def verify_api_key(request: "Request") -> dict:
    """Verify API key from header or query param. Returns key info."""
    key = request.headers.get("X-API-Key", "") or request.query_params.get("api_key", "")

    # No key = internal/local access (no restrictions)
    if not key and request.client and request.client.host in ("127.0.0.1", "localhost", "::1"):
        return {"tier": "internal", "daily_limit": 999999}

    # No key from external = use demo tier
    if not key:
        key = "wave_demo_2026"

    if key not in _API_KEYS:
        return None  # will raise 401

    return _API_KEYS[key]


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
    title="Wave API — Autonomous Soul Architecture",
    description=(
        "Autonomous AI agent with 158 tools, 10 specialist agents, and a 19-subsystem "
        "cognitive architecture. Built on the Autonomous Soul Architecture (ASA) and "
        "Psychometric Utility Theory (PUT). Created by Manuel Galmanus.\n\n"
        "**Tiers:**\n"
        "- Free: 10 requests/day, demo key `wave_demo_2026`\n"
        "- Pro: 1000 requests/day, full tools (contact m.galmanus@gmail.com)\n"
        "- Enterprise: unlimited, Opus model (contact m.galmanus@gmail.com)\n\n"
        "**Authentication:** Pass API key via `X-API-Key` header."
    ),
    version="2.0.0",
)

CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS[0] else ["*"],
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
    _load_api_keys()
    logger.info("API keys loaded: %d keys (%s)", len(_API_KEYS),
                ", ".join(k.get("tier", "?") for k in _API_KEYS.values()))
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


@app.get("/pricing")
async def pricing():
    """API pricing tiers. Premium first — the Musk doctrine."""
    return {
        "philosophy": "Wave has no equivalent. The pricing reflects the value of something that cannot be obtained elsewhere at any price. We never discount.",
        "tiers": {
            "spectacle": {
                "price": "$0/month",
                "requests_per_day": 10,
                "model": "Haiku",
                "tools": "Limited — brand compliance, basic content, demo",
                "api_key": "wave_demo_2026",
                "purpose": "Experience Wave. See what autonomous cognitive architecture produces. Then decide if you can afford NOT to have it.",
            },
            "operator": {
                "price": "$149/month",
                "requests_per_day": 500,
                "model": "Haiku + Sonnet",
                "tools": "Brand compliance (8 dimensions), content generation (7 channels), basic PUT analysis, basic competitive intel",
                "margin": "96.6%",
                "target": "Individual operators, freelancers, small agencies",
            },
            "commander": {
                "price": "$499/month",
                "requests_per_day": 5000,
                "model": "Haiku + Sonnet + Opus (auto-selected)",
                "tools": "Full 158 tools — OSINT, security audits, full PUT (FP scoring, ignition detection, shadow scan), kill chain, pre-mortem, prospect qualification (BANT + PUT)",
                "margin": "95%",
                "target": "Agencies, growth teams, sales operations, security firms",
            },
            "sovereign": {
                "price": "$2,499/month",
                "requests_per_day": "Unlimited",
                "model": "All models + extended thinking",
                "tools": "Everything + Agent Factory (dedicated child agents), custom soul specifications, MIDAS integration, white-label, quarterly PUT calibration, direct Telegram channel, monthly strategy session with Manuel",
                "margin": "92%",
                "target": "Enterprise, funds, institutions",
                "note": "Limited to 10 clients per quarter. Waitlist applies.",
            },
            "alliance": {
                "price": "$10,000+/month",
                "requests_per_day": "Unlimited",
                "model": "All models + priority",
                "tools": "Everything + dedicated instance, custom ASA adaptation, PUT calibrated on your data, source access (read-only), co-authored research, advisory services",
                "target": "META, Anthropic, xAI, sovereign funds, large enterprises",
                "note": "Strategic partnership, not vendor relationship. Contact Manuel directly.",
            },
        },
        "why_this_price": {
            "no_equivalent": "The Autonomous Soul Architecture and Psychometric Utility Theory do not exist anywhere else. You cannot get this from OpenAI, Google, or any competitor.",
            "original_research": "Two published whitepapers with axiomatic derivation, ODE systems, and Lyapunov stability proofs. This is not a wrapper around ChatGPT.",
            "production_proven": "130+ autonomous decision cycles. 158 tools. 47 modules. Running since February 2026.",
            "margin_justified": "API costs are <5% of price. The other 95% is the value of original IP that took decades of lived experience to create.",
        },
        "anti_discount_policy": "We do not discount. The price is the price because the value is the value. If a tier doesn't fit your budget, use the tier below. There is no 'special deal.'",
        "contact": "m.galmanus@gmail.com",
        "documentation": "https://github.com/Galmanus/bluewave",
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    """Send a message to the orchestrator and get a response.

    Authentication: pass API key via X-API-Key header.
    Free tier: 10 requests/day with key 'wave_demo_2026'.
    """
    if not req.message.strip():
        raise HTTPException(400, "Empty message")

    # Verify API key
    key_info = verify_api_key(request)
    if key_info is None:
        raise HTTPException(401, "Invalid API key. Get a free key at /pricing")

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
    from brand_suite import generate_social_calendar
    b = await request.json()
    weeks = max(1, min(int(b.get("weeks", 4)), 12))
    posts_per_week = max(1, min(int(b.get("posts_per_week", 5)), 14))
    t0 = time.time()
    r = await generate_social_calendar(
        weeks, posts_per_week,
        b.get("channels", "instagram_feed,instagram_stories"),
        b.get("themes", ""), b.get("language", "pt-BR"),
    )
    return {"content": r, "elapsed_seconds": time.time() - t0}


@app.post("/brand/repurpose")
async def repurpose(request: Request):
    from brand_suite import repurpose_content
    b = await request.json()
    content = b.get("content", "")
    if not content:
        raise HTTPException(400, "content is required")
    t0 = time.time()
    r = await repurpose_content(content, b.get("channel", "instagram_feed"), b.get("language", "pt-BR"))
    return {"content": r, "elapsed_seconds": time.time() - t0}


@app.post("/brand/ad-copy")
async def ad_copy(request: Request):
    from brand_suite import generate_ad_copy
    b = await request.json()
    product = b.get("product", "")
    if not product:
        raise HTTPException(400, "product is required")
    variations = max(1, min(int(b.get("variations", 3)), 10))
    t0 = time.time()
    r = await generate_ad_copy(
        product, b.get("objective", "conversions"),
        b.get("audience", ""), variations, b.get("language", "pt-BR"),
    )
    return {"content": r, "elapsed_seconds": time.time() - t0}


@app.post("/brand/email-sequence")
async def email_seq(request: Request):
    from brand_suite import generate_email_sequence
    b = await request.json()
    count = max(1, min(int(b.get("count", 5)), 20))
    t0 = time.time()
    r = await generate_email_sequence(
        b.get("type", "welcome"), count,
        b.get("product", ""), b.get("language", "pt-BR"),
    )
    return {"content": r, "elapsed_seconds": time.time() - t0}


@app.post("/brand/product-descriptions")
async def prod_desc(request: Request):
    from brand_suite import generate_product_descriptions
    b = await request.json()
    products = b.get("products", [])
    if not products or not isinstance(products, list):
        raise HTTPException(400, "products must be a non-empty list")
    if len(products) > 50:
        raise HTTPException(400, "Maximum 50 products per request")
    t0 = time.time()
    r = await generate_product_descriptions(products, b.get("style", "short"), b.get("language", "pt-BR"))
    return {"content": r, "elapsed_seconds": time.time() - t0}


@app.post("/brand/hashtags")
async def hashtags(request: Request):
    from brand_suite import research_hashtags
    b = await request.json()
    topic = b.get("topic", "")
    if not topic:
        raise HTTPException(400, "topic is required")
    count = max(1, min(int(b.get("count", 15)), 50))
    t0 = time.time()
    r = await research_hashtags(topic, count, b.get("language", "pt-BR"))
    return {"content": r, "elapsed_seconds": time.time() - t0}


@app.post("/brand/competitor-audit")
async def comp_audit(request: Request):
    from brand_suite import audit_competitor_content
    b = await request.json()
    competitor = b.get("competitor", "")
    if not competitor:
        raise HTTPException(400, "competitor is required")
    t0 = time.time()
    r = await audit_competitor_content(competitor, b.get("description", ""), b.get("language", "pt-BR"))
    return {"content": r, "elapsed_seconds": time.time() - t0}


@app.post("/brand/report")
async def brand_report(request: Request):
    from brand_suite import generate_brand_report
    b = await request.json()
    t0 = time.time()
    r = await generate_brand_report(
        b.get("period", "monthly"), b.get("scores", []),
        max(0, int(b.get("content_generated", 0))), b.get("language", "pt-BR"),
    )
    return {"content": r, "elapsed_seconds": time.time() - t0}


# ── Brand DNA Extraction (R$997 setup service) ──────────────

@app.post("/brand/extract-dna")
async def extract_dna(request: Request):
    """Extract complete Brand DNA from uploaded materials.

    Accepts: image (base64), text description, or PDF text.
    Returns: structured Brand DNA JSON ready for compliance checking.

    This is the premium setup service (R$997/brand).
    """
    import time as _time
    from brand_dna_extractor import extract_brand_dna

    body = await request.json()
    t0 = _time.time()

    result = await extract_brand_dna(
        image_b64=body.get("image_base64"),
        media_type=body.get("media_type", "image/jpeg"),
        text_content=body.get("text_content"),
        pdf_text=body.get("pdf_text"),
        brand_name=body.get("brand_name", ""),
    )

    elapsed = _time.time() - t0
    logger.info("Brand DNA extraction: %.1fs, success=%s", elapsed, result.get("success"))
    return {**result, "elapsed_seconds": round(elapsed, 2)}


# ── Compliance Certificate ───────────────────────────────────

@app.post("/brand/certificate")
async def compliance_certificate(request: Request):
    """Generate a compliance certificate for a checked asset.

    Input: brand_name, asset_name, score, dimensions, checked_at
    Output: certificate text (can be rendered as PDF by frontend)

    Revenue: R$9,90 per certificate.
    """
    from brand_dna_extractor import generate_compliance_certificate

    body = await request.json()
    cert = await generate_compliance_certificate(
        brand_name=body.get("brand_name", ""),
        asset_name=body.get("asset_name", ""),
        score=body.get("score", 0),
        dimensions=body.get("dimensions", {}),
        checked_at=body.get("checked_at", ""),
    )
    return {"certificate": cert}


# ── Public API: Per-Check Compliance (R$0,50/check) ─────────

@app.post("/api/v1/compliance-check")
async def public_compliance_check(request: Request):
    """Public API for per-check brand compliance.

    Requires X-API-Key header. Each check costs R$0,50.
    Designed for agencies integrating compliance into their workflows.

    Input: image_base64 + media_type
    Output: compliance report with score, dimensions, issues, fixes
    """
    import time as _time
    from brand_vision import analyze_brand_compliance

    # Validate API key
    api_key = request.headers.get("X-API-Key", "")
    if not api_key:
        raise HTTPException(401, "X-API-Key header required")

    body = await request.json()
    image_b64 = body.get("image_base64", "")
    media_type = body.get("media_type", "image/jpeg")

    if not image_b64 or len(image_b64) < 100:
        raise HTTPException(400, "Valid image_base64 required")

    t0 = _time.time()
    result = await analyze_brand_compliance(image_b64, media_type)
    elapsed = _time.time() - t0

    logger.info("Public API compliance check: %.1fs", elapsed)
    return {
        "report": result,
        "elapsed_seconds": round(elapsed, 2),
        "billing": {
            "cost_brl": 0.50,
            "method": "per-check",
        },
    }


# ── Main ─────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
