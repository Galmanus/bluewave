"""
bitchat_lan — Wave skill: P2P intranet soberana na LAN física
=============================================================
Rede social restrita ao espaço físico de trabalho.
Sem servidor central. Sem admin. Sem vigilância.

Discovery  : UDP broadcast 55420
Transport  : TCP 55421
Identity   : Ed25519 keypair local
Channels   : #general #midas #zk #ops #wave
"""

from __future__ import annotations
import asyncio
import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("openclaw.bitchat_lan")

NODE_SCRIPT = Path(__file__).parent / "bitchat_node.py"


def _run_node(args: list, timeout: int = 12) -> dict:
    """Executa o nó BitChat como subprocess e retorna stdout parseado."""
    try:
        result = subprocess.run(
            [sys.executable, str(NODE_SCRIPT)] + args,
            capture_output=True, text=True, timeout=timeout
        )
        output  = result.stdout.strip()
        stderr  = result.stderr.strip()

        # tenta extrair JSON do output
        status_json = None
        try:
            lines = output.split("\n")
            idx   = next((i for i, l in enumerate(lines) if l.startswith("{")), None)
            if idx is not None:
                status_json = json.loads("\n".join(lines[idx:]))
        except Exception:
            pass

        return {
            "ok":      result.returncode == 0,
            "parsed":  status_json,
            "output":  output,
            "stderr":  stderr[:400] if stderr else ""
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timeout after {timeout}s"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def bitchat_scan(params: Dict[str, Any]) -> dict:
    """Escaneia a LAN por nós BitChat ativos."""
    alias   = params.get("alias", "wave")
    timeout = int(params.get("timeout", 20))

    r = _run_node(["--alias", alias, "--scan"], timeout=timeout + 10)
    parsed  = r.get("parsed") or {}
    peers   = parsed.get("peers", [])

    return {
        "success": True,
        "data": {
            "node_id":    parsed.get("node_id", "unknown"),
            "alias":      parsed.get("alias", alias),
            "live_peers": parsed.get("live_peers", 0),
            "peers":      peers,
            "interfaces": parsed.get("interfaces", []),
            "channels":   parsed.get("channels", {}),
        },
        "message": (
            f"{len(peers)} peer(s) encontrado(s) na LAN"
            if peers else
            "Nenhum par encontrado. Nó aguarda descoberta."
        )
    }


async def bitchat_send(params: Dict[str, Any]) -> dict:
    """Envia mensagem para todos os pares na LAN."""
    text    = params.get("text", "")
    channel = params.get("channel", "#general")
    alias   = params.get("alias", "wave")

    if not text:
        return {"success": False, "data": None, "message": "text é obrigatório"}

    r = _run_node(["--alias", alias, "--send", text, "--channel", channel])

    return {
        "success": r["ok"] or "SENT" in r.get("output", ""),
        "data": {"channel": channel, "text": text, "output": r.get("output", "")},
        "message": f"Mensagem enviada para {channel}" if r["ok"] else r.get("error", "erro desconhecido")
    }


async def bitchat_status(params: Dict[str, Any]) -> dict:
    """Mostra estado do nó local — identidade, peers, canais."""
    alias = params.get("alias", "wave")
    r     = _run_node(["--alias", alias, "--status"])
    p     = r.get("parsed") or {}

    return {
        "success": True,
        "data": p or {"output": r.get("output", ""), "error": r.get("stderr", "")},
        "message": (
            f"Nó '{p.get('alias', alias)}' — {p.get('live_peers', 0)} peer(s) vivo(s)"
            if p else "Nó inicializado. Aguardando descoberta."
        )
    }


# ── TOOLS registration ────────────────────────────────────────────────────────

TOOLS = [
    {
        "name":        "bitchat_scan",
        "description": (
            "Scan LAN for active BitChat nodes (P2P intranet). "
            "Discovers peers in the physical workspace via UDP broadcast. "
            "No server needed. Use before sending messages."
        ),
        "handler":     bitchat_scan,
        "parameters": {
            "type": "object",
            "properties": {
                "alias":   {"type": "string",  "default": "wave",
                            "description": "Node alias (visible to peers)"},
                "timeout": {"type": "integer", "default": 20,
                            "description": "Scan duration in seconds"},
            },
            "required": [],
        },
    },
    {
        "name":        "bitchat_send",
        "description": (
            "Send a message to all peers on the LAN intranet via BitChat. "
            "Signed with Ed25519 — cannot be forged. No server reads this."
        ),
        "handler":     bitchat_send,
        "parameters": {
            "type": "object",
            "properties": {
                "text":    {"type": "string",  "description": "Message text"},
                "channel": {"type": "string",  "default": "#general",
                            "description": "Channel: #general #midas #zk #ops #wave"},
                "alias":   {"type": "string",  "default": "wave",
                            "description": "Sender alias"},
            },
            "required": ["text"],
        },
    },
    {
        "name":        "bitchat_status",
        "description": (
            "Show local BitChat node status — identity (node_id, pub key), "
            "live peers, channel message counts, network interfaces."
        ),
        "handler":     bitchat_status,
        "parameters": {
            "type": "object",
            "properties": {
                "alias": {"type": "string", "default": "wave",
                          "description": "Node alias"},
            },
            "required": [],
        },
    },
]
