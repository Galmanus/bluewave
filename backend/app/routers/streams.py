"""Traakeer Streams Router — behavioral signal ingestion for PUT psychometrics.

Receives heartbeats from traakeer-streams.ts (frontend SDK) via:
  - WebSocket:  ws://<host>/api/v1/streams/session/{session_id}
  - HTTP POST:  POST /api/v1/streams/event  (fallback / sendBeacon)

Each heartbeat contains: mouse metrics, scroll metrics, keystroke dynamics,
gaze proxy, and event counts — raw behavioral fuel for the PUT engine.

Storage: async queue → JSONL file per session (memory/streams/{session_id}.jsonl)
         In production, upgrade to Redis stream or PostgreSQL.
"""

import asyncio
import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("bluewave.streams")

router = APIRouter(prefix="/streams", tags=["streams"])

# ── Storage ─────────────────────────────────────────────────────────────────

STREAMS_DIR = Path(os.environ.get("STREAMS_DIR", "/tmp/bluewave_streams"))
STREAMS_DIR.mkdir(parents=True, exist_ok=True)

# In-memory registry: session_id → list of recent heartbeats (last 60)
_session_buffer: Dict[str, list] = defaultdict(list)
_BUFFER_MAX = 60  # ~1 minute at 1hz

# Active WebSocket connections: session_id → WebSocket
_active_ws: Dict[str, WebSocket] = {}


def _store_heartbeat(session_id: str, payload: Dict[str, Any]) -> None:
    """Append heartbeat to in-memory buffer + JSONL file."""
    payload.setdefault("received_at", datetime.now(timezone.utc).isoformat())
    payload.setdefault("session_id", session_id)

    # In-memory (last 60 samples per session)
    buf = _session_buffer[session_id]
    buf.append(payload)
    if len(buf) > _BUFFER_MAX:
        _session_buffer[session_id] = buf[-_BUFFER_MAX:]

    # Persist to disk
    try:
        session_file = STREAMS_DIR / f"{session_id}.jsonl"
        with open(session_file, "a") as f:
            f.write(json.dumps(payload, default=str) + "\n")
    except Exception as exc:
        logger.warning("Stream persistence failed for %s: %s", session_id, exc)


# ── HTTP fallback endpoint ───────────────────────────────────────────────────

@router.post("/event")
async def ingest_event(request: Request):
    """HTTP fallback for traakeer-streams.ts sendBeacon / fetch POST.

    Accepts Content-Type: application/json
    Body: Heartbeat JSON blob (see traakeer-streams.ts interface Heartbeat)
    """
    try:
        payload = await request.json()
    except Exception:
        # sendBeacon may send raw text — try body decode
        try:
            raw = await request.body()
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            return JSONResponse({"ok": False, "error": "invalid_json"}, status_code=400)

    session_id = payload.get("session_id", "unknown")
    _store_heartbeat(session_id, payload)

    logger.debug(
        "Stream heartbeat [HTTP] session=%s events=%s",
        session_id, payload.get("event_count", 0)
    )
    return JSONResponse({"ok": True, "session_id": session_id})


# ── WebSocket endpoint ───────────────────────────────────────────────────────

@router.websocket("/session/{session_id}")
async def stream_session(websocket: WebSocket, session_id: str):
    """WebSocket for real-time behavioral stream from traakeer-streams.ts.

    Client sends Heartbeat JSON every HEARTBEAT_MS (1s).
    Server stores and may respond with PUT feedback (future: P(t) update).
    """
    await websocket.accept()
    _active_ws[session_id] = websocket

    logger.info("Stream WS connected: session=%s", session_id)

    try:
        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                # Send keepalive ping
                await websocket.send_text(json.dumps({"type": "ping"}))
                continue

            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue

            _store_heartbeat(session_id, payload)

            logger.debug(
                "Stream heartbeat [WS] session=%s events=%s",
                session_id, payload.get("event_count", 0)
            )

            # Optional: echo P(t) back to client (placeholder — wire to PUT engine later)
            await websocket.send_text(json.dumps({
                "type": "ack",
                "session_id": session_id,
                "ts": payload.get("ts"),
            }))

    except WebSocketDisconnect:
        logger.info("Stream WS disconnected: session=%s", session_id)
    except Exception as exc:
        logger.warning("Stream WS error [%s]: %s", session_id, exc)
    finally:
        _active_ws.pop(session_id, None)


# ── Session query endpoint ───────────────────────────────────────────────────

@router.get("/session/{session_id}/buffer")
async def get_session_buffer(session_id: str):
    """Return the last N heartbeats buffered for a session.

    Used by the dashboard Streams view to pull live behavioral data.
    """
    buf = _session_buffer.get(session_id, [])
    return {
        "session_id": session_id,
        "count": len(buf),
        "heartbeats": buf[-20:],  # last 20 samples
        "active_ws": session_id in _active_ws,
    }


@router.get("/active")
async def list_active_sessions():
    """List all sessions with data in the buffer (last 5 minutes)."""
    now = datetime.now(timezone.utc)
    active = []
    for sid, buf in _session_buffer.items():
        if not buf:
            continue
        last = buf[-1]
        active.append({
            "session_id": sid,
            "heartbeat_count": len(buf),
            "last_ts": last.get("ts"),
            "last_page": last.get("page"),
            "user_id": last.get("user_id"),
            "ws_connected": sid in _active_ws,
        })
    return {"active_sessions": active, "count": len(active)}
