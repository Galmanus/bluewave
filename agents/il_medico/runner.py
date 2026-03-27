#!/usr/bin/env python3
"""il_cacciatore — Autonomous child agent created by Wave.

Runs a deliberation loop using Claude CLI (free on Max plan).
Reports to Wave (parent agent).
"""

import asyncio
import json
import logging
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
logger = logging.getLogger("agent.il_medico")

SOUL_PATH = Path(__file__).parent / "soul.json"
STATE_PATH = Path(__file__).parent / "state.json"
TASK_QUEUE = Path(__file__).parent / "tasks.jsonl"
RESULTS_LOG = Path(__file__).parent / "results.jsonl"

MODEL = "haiku"
MIN_INTERVAL = 300
MAX_INTERVAL = 1800


def load_soul():
    return json.loads(SOUL_PATH.read_text(encoding="utf-8"))


def load_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"energy": 0.8, "total_cycles": 0, "consciousness": "dormant", "recent_actions": []}


def save_state(state):
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.rename(STATE_PATH)


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


async def deliberate(soul, state, task=None):
    """Deliberate using Claude CLI — free on Max plan."""
    soul_text = json.dumps(soul, indent=2)[:6000]

    prompt = "State: energy=%.1f, cycles=%d, consciousness=%s\n" % (
        state["energy"], state["total_cycles"], state["consciousness"]
    )
    if task:
        prompt += "\nPENDING TASK from Wave: %s\n" % task.get("description", "")
    prompt += "\nDecide: observe, research, report, execute, or silence. Respond with JSON."

    # Write soul as system prompt file
    sys_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, dir='/tmp')
    sys_file.write(soul_text)
    sys_file.close()

    try:
        env = os.environ.copy()
        env["CLAUDE_CODE_ENTRYPOINT"] = "api"

        proc = await asyncio.create_subprocess_exec(
            "claude", "-p", prompt, "--model", MODEL, "--system-prompt-file", sys_file.name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)

        if proc.returncode == 0:
            return stdout.decode("utf-8", errors="replace").strip()
        else:
            logger.error("CLI exit=%d: %s", proc.returncode, stderr.decode()[:200])
            return None
    except asyncio.TimeoutError:
        proc.kill()
        logger.warning("CLI timeout after 60s")
        return None
    except Exception as e:
        logger.error("Deliberation failed: %s", e)
        return None
    finally:
        try:
            os.unlink(sys_file.name)
        except Exception:
            pass


async def main():
    soul = load_soul()
    logger.info("il_medico started. Soul loaded. Engine: Claude CLI (Max plan).")

    while True:
        state = load_state()
        task = check_tasks()

        result = await deliberate(soul, state, task)

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
