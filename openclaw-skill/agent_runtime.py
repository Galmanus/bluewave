import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

@dataclass
class AgentConfig:
    agent_id: str
    name: str
    emoji: str
    system_prompt: str
    tool_names: List[str]
    description: str = ""

@dataclass
class AgentResult:
    agent_id: str
    text: str
    tool_calls_made: int = 0
    turns_used: int = 0
    error: Optional[str] = None

class AgentRuntime:
    def __init__(self, config, all_tools, handler, model=None):
        self.config = config
        self.handler = handler
        self.history = []

    async def run(self, user_message, context=None):
        from gemini_engine import gemini_call
        full_msg = f"{user_message}\n\nContext: {context}" if context else user_message
        res = await gemini_call(full_msg, system_prompt=self.config.system_prompt, history=self.history)
        if res["success"]:
            self.history.append({"role": "user", "content": full_msg})
            self.history.append({"role": "model", "content": res["response"]})
            return AgentResult(self.config.agent_id, text=res["response"])
        return AgentResult(self.config.agent_id, text=res["response"], error=res["response"])

def load_all_tools(): return []
def load_prompt(f):
    p = Path("prompts") / f
    return p.read_text(encoding="utf-8") if p.exists() else "You are Wave."
def enhance_prompt_with_cognition(aid, p): return p
