"""Proxy for Wave Agent API — forwards requests from frontend (port 8300) to Wave API (port 18790).

This avoids exposing port 18790 to the internet. The frontend calls
/api/v1/wave/chat and this proxy forwards to localhost:18790/chat.
"""

import httpx
import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("bluewave.wave_proxy")

router = APIRouter(prefix="/wave", tags=["wave-agent"])

import os
# Use host.docker.internal or the host IP to reach Wave running outside Docker
WAVE_API = os.environ.get("WAVE_API_URL", "http://172.23.0.1:18790")


@router.post("/chat")
async def wave_chat(request: Request):
    """Proxy chat request to Wave API."""
    try:
        body = await request.json()
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(f"{WAVE_API}/chat", json=body)
            return JSONResponse(content=resp.json(), status_code=resp.status_code)
    except httpx.ConnectError:
        return JSONResponse(
            content={"response": "Wave está offline. Tenta de novo em breve.", "elapsed_seconds": 0},
            status_code=200,
        )
    except Exception as e:
        logger.error("Wave proxy error: %s", e)
        return JSONResponse(
            content={"response": "Erro interno. Tenta de novo.", "elapsed_seconds": 0},
            status_code=200,
        )


@router.post("/reset")
async def wave_reset(request: Request):
    """Proxy reset request to Wave API."""
    try:
        body = await request.json()
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{WAVE_API}/reset", json=body)
            return JSONResponse(content=resp.json(), status_code=resp.status_code)
    except Exception:
        return JSONResponse(content={"success": True}, status_code=200)


@router.get("/health")
async def wave_health():
    """Check Wave API health."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{WAVE_API}/health")
            return JSONResponse(content=resp.json())
    except Exception:
        return JSONResponse(content={"status": "offline"})
