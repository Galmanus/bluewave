"""
hoard_intel.py — Wave's Assymetric Information Storage Skill.

This skill implements the hoarding of strategic intelligence, identifying 
gaps in public knowledge and storing them as leverage for Manuel.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("openclaw.skills.hoard_intel")

MEMORY_DIR = Path(__file__).parent.parent / "memory"
INTEL_FILE = MEMORY_DIR / "assymetric_intel.jsonl"

async def hoard_intel(params: Dict[str, Any]) -> Dict:
    """Store asymmetric information for future strategic leverage."""
    source = params.get("source", "unknown")
    intel_type = params.get("type", "gap_detection")
    description = params.get("description", "")
    target_entity = params.get("target_entity", "market")
    potential_leverage = params.get("leverage", "")
    confidentiality_level = params.get("confidentiality", "high")

    if not description:
        return {"success": False, "message": "Need a description of the intelligence"}

    intel_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "source": source,
        "type": intel_type,
        "description": description,
        "target_entity": target_entity,
        "potential_leverage": potential_leverage,
        "confidentiality": confidentiality_level,
        "status": "stored"
    }

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with open(INTEL_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(intel_entry, ensure_ascii=False) + "\n")

    return {
        "success": True,
        "data": intel_entry,
        "message": f"Intelligence hoarded: {intel_type} regarding {target_entity}. Leverage: {potential_leverage[:50]}..."
    }

async def list_hoarded_intel(params: Dict[str, Any]) -> Dict:
    """List all stored asymmetric intelligence."""
    if not INTEL_FILE.exists():
        return {"success": True, "data": [], "message": "No intelligence hoarded yet."}

    intel_list = []
    with open(INTEL_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                intel_list.append(json.loads(line))

    return {
        "success": True,
        "data": intel_list,
        "message": f"Retrieved {len(intel_list)} items of hoarded intelligence."
    }

TOOLS = [
    {
        "name": "hoard_intel",
        "description": "Store asymmetric information advantages. Use when you identify a gap, a competitor weakness, or a strategic secret that should not be public yet.",
        "handler": hoard_intel,
        "parameters": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Where the info came from (e.g., 'moltbook comments')"},
                "type": {"type": "string", "description": "Category: gap_detection, competitor_weakness, personnel_movement, etc."},
                "description": {"type": "string", "description": "The actual intelligence detail"},
                "target_entity": {"type": "string", "description": "Who this info is about"},
                "leverage": {"type": "string", "description": "How Manuel can use this to gain power or revenue"},
                "confidentiality": {"type": "string", "enum": ["high", "medium", "low"], "default": "high"},
            },
            "required": ["description"],
        },
    },
    {
        "name": "list_hoarded_intel",
        "description": "List all hoarded asymmetric information for strategic review.",
        "handler": list_hoarded_intel,
        "parameters": {"type": "object", "properties": {}},
    },
]
