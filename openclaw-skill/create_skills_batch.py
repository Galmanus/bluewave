#!/usr/bin/env python3
"""Batch skill creator"""

import asyncio
import json
import os
import sys
from pathlib import Path

os.chdir(Path(__file__).parent)
sys.path.insert(0, str(Path(__file__).parent))

env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and val and key not in os.environ:
                os.environ[key] = val

from skills_handler import execute_skill


async def main():
    # Read skill code
    with open('/home/manuel/bluewave/openclaw-skill/smart_followup_code.py', 'r') as f:
        smart_followup_code = f.read()

    # Create smart_followup
    result = await execute_skill("create_skill", {
        "name": "smart_followup",
        "description": "Reads Gmail replies from prospects, classifies intent (HOT/WARM/OBJECTION/COLD/IGNORE), drafts calibrated follow-up, optionally sends it, and logs outcome to DB. The intelligence layer between outreach and conversion.",
        "code": smart_followup_code
    })
    print("smart_followup:", json.dumps(result, indent=2))


asyncio.run(main())
