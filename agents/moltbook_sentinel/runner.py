#!/usr/bin/env python3
"""moltbook_sentinel — Autonomous child agent created by Wave.

Runs a deliberation loop using its soul specification.
Reports to Wave (parent agent).
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

import anthropic

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
logger = logging.getLogger("agent.moltbook_sentinel")

SOUL_PATH = Path(__file__).parent / "soul.json"
STATE_PATH = Path(__file__).parent / "state.json"
TASK_QUEUE = Path(__file__).parent / "tasks.jsonl"
RESULTS_LOG = Path(__file__).parent / "results.jsonl"

MODEL = "claude-haiku-4-5-20251001"
MIN_INTERVAL = 300
MAX_INTERVAL = 1800


def load_soul():
    return json.loads(SOUL_PATH.read_text(encoding="utf-8"))


def load_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"energy": 0.8, "total_cycles": 0, "consciousness": "dormant", "recent_actions": []}


def save_state(state):
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def check_tasks():
    if not TASK_QUEUE.exists():
        return None
    lines = TASK_QUEUE.read_text(encoding="utf-8").strip().split("\n")
    for line in lines:
        if line.strip():
            try:
                task = json.loads(line)
                if not task.get("completed"):
                    return task
            except json.JSONDecodeError:
                continue
    return None


def log_result(result):
    with open(RESULTS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")


async def deliberate(client, soul, state, task=None):
    soul_text = json.dumps(soul, indent=2)[:6000]

    prompt = "State: energy=%.1f, cycles=%d, consciousness=%s\n" % (
        state["energy"], state["total_cycles"], state["consciousness"]
    )
    if task:
        prompt += "\nPENDING TASK from Wave: %s\n" % task.get("description", "")
    prompt += "\nDecide: observe, research, report, execute, or silence. Respond with JSON."

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=[{"type": "text", "text": soul_text, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except Exception as e:
        logger.error("Deliberation failed: %s", e)
        return None


async def main():
    client = anthropic.Anthropic()
    soul = load_soul()
    logger.info("moltbook_sentinel started. Soul loaded.")

    while True:
        state = load_state()
        task = check_tasks()

        result = await deliberate(client, soul, state, task)

        state["total_cycles"] += 1
        state["recent_actions"].append({
            "time": datetime.utcnow().isoformat() + "Z",
            "result_preview": (result or "")[:200],
        })
        state["recent_actions"] = state["recent_actions"][-10:]
        save_state(state)

        if result:
            log_result({"cycle": state["total_cycles"], "time": datetime.utcnow().isoformat(), "result": result[:500]})

        interval = MIN_INTERVAL + (MAX_INTERVAL - MIN_INTERVAL) * (1 - state["energy"])
        logger.info("Cycle %d complete. Energy: %.1f. Next in %ds.", state["total_cycles"], state["energy"], interval)
        await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(main())
