import json
from pathlib import Path
from agent_runtime import AgentConfig, AgentRuntime, load_prompt

class Orchestrator:
    def __init__(self, handler=None):
        self.handler = handler
        self.history = []
        with open("agents.json", "r") as f:
            data = json.load(f)
        orch = data["orchestrator"]
        self.system_prompt = load_prompt(orch["soul_prompt_file"].replace("prompts/", ""))

    async def chat(self, user_message: str) -> str:
        from gemini_engine import gemini_call
        res = await gemini_call(user_message, system_prompt=self.system_prompt, history=self.history)
        if res["success"]:
            self.history.append({"role": "user", "content": user_message})
            self.history.append({"role": "model", "content": res["response"]})
            return res["response"]
        return f"Erro: {res['response']}"
