"""OpenClaw HTTP API Server — expose the agent system via REST (Gemini Edition).

Endpoints:
    POST /chat              → Send a message, get agent response
    POST /chat/stream       → Send a message, get SSE stream
    GET  /agents            → List available agents
    POST /reset             → Reset conversation
    GET  /health            → Health check

Usage:
    python api.py                          # start server on port 18790

Environment:
    GEMINI_API_KEY        — required
    BLUEWAVE_API_URL      — Bluewave backend URL
    BLUEWAVE_API_KEY      — Bluewave API key
    OPENCLAW_PORT         — server port (default: 18790)
    OPENCLAW_MODEL        — Gemini model override
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
    print("Install dependencies: pip install fastapi uvicorn httpx google-genai")
    sys.exit(1)

from orchestrator import Orchestrator
from handler import BlueWaveHandler

# ── Config ────────────────────────────────────────────────────

PORT = int(os.environ.get("OPENCLAW_PORT", "18790"))

# ── API Key Tiers ──────────────────────────

API_KEYS_FILE = os.path.join(os.path.dirname(__file__), "memory", "api_keys.json")
_API_KEYS = {}

def _load_api_keys():
    global _API_KEYS
    _API_KEYS.setdefault("wave_demo_2026", {
        "owner": "demo",
        "tier": "free",
        "daily_limit": 10,
        "models": ["gemini-2.0-flash-lite"],
    })

def verify_api_key(request: Request) -> dict:
    key = request.headers.get("X-API-Key", "") or request.query_params.get("api_key", "")
    if not key and request.client and request.client.host in ("127.0.0.1", "localhost", "::1"):
        return {"tier": "internal", "daily_limit": 999999}
    if not key:
        key = "wave_demo_2026"
    return _API_KEYS.get(key)

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"

class ChatResponse(BaseModel):
    response: str
    session_id: str
    elapsed_seconds: float

app = FastAPI(
    title="Wave API — Gemini Sovereign Engine",
    description="Autonomous AI agent powered by Google Gemini. ASA & PUT architecture.",
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions = {}
handler_obj = None

def get_orchestrator(session_id: str = "default") -> Orchestrator:
    if session_id not in sessions:
        sessions[session_id] = Orchestrator(handler=handler_obj)
    return sessions[session_id]

@app.on_event("startup")
async def startup():
    global handler_obj
    _load_api_keys()
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        logger.error("GEMINI_API_KEY not set!")
        return
    try:
        handler_obj = BlueWaveHandler()
    except:
        pass
    logger.info(f"🌊 Wave API (Gemini) ready on port {PORT}")

@app.get("/health")
async def health():
    return {"status": "ok", "engine": "gemini-2.0", "sessions": len(sessions)}

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    if not req.message.strip():
        raise HTTPException(400, "Empty message")
    
    key_info = verify_api_key(request)
    if key_info is None:
        raise HTTPException(401, "Invalid API key")

    orch = get_orchestrator(req.session_id)
    t0 = time.time()
    response = await orch.chat(req.message)
    elapsed = time.time() - t0

    return ChatResponse(
        response=response,
        session_id=req.session_id,
        elapsed_seconds=round(elapsed, 2),
    )

@app.post("/reset")
async def reset_session(session_id: str = "default"):
    if session_id in sessions:
        sessions[session_id].history = []
        return {"status": "reset"}
    return {"status": "no_session"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
