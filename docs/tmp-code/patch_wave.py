#!/usr/bin/env python3
"""Patch Wave orchestrator to use claude -p as primary engine."""

import sys

filepath = "/home/manuel/bluewave/openclaw-skill/orchestrator.py"

with open(filepath, "r") as f:
    lines = f.readlines()

# Find line with "return self.client.messages.create(**kwargs)"
# and the try block above it. Replace with CLI-first approach.

new_lines = []
skip_until_except = False
inserted = False

for i, line in enumerate(lines):
    # Find the try block that contains messages.create
    if "return self.client.messages.create(**kwargs)" in line and not inserted:
        # Go back and find the "try:" that starts this block
        # Insert CLI engine before the try
        # Find where "try:" was
        try_idx = None
        for j in range(len(new_lines) - 1, -1, -1):
            if new_lines[j].strip() == "try:":
                try_idx = j
                break

        if try_idx is not None:
            # Remove everything from try: to current line
            new_lines = new_lines[:try_idx]

            indent = "        "
            cli_block = [
                f"{indent}# PRIMARY: claude -p (Pro Max, Opus, FREE)\n",
                f"{indent}try:\n",
                f"{indent}    from claude_cli_engine import cli_call_structured\n",
                f"{indent}    from types import SimpleNamespace\n",
                f"{indent}    cli_response = cli_call_structured(\n",
                f"{indent}        system_prompt=use_system,\n",
                f"{indent}        messages=managed_messages,\n",
                f'{indent}        model="claude-opus-4-20250514",\n',
                f"{indent}    )\n",
                f'{indent}    content_block = SimpleNamespace(type="text", text=cli_response)\n',
                f"{indent}    mock_response = SimpleNamespace(\n",
                f"{indent}        content=[content_block],\n",
                f'{indent}        stop_reason="end_turn",\n',
                f'{indent}        model="claude-opus-4-20250514",\n',
                f"{indent}        usage=SimpleNamespace(input_tokens=0, output_tokens=len(cli_response.split())),\n",
                f"{indent}    )\n",
                f'{indent}    logger.info("CLI engine OK (%d chars, Opus)", len(cli_response))\n',
                f"{indent}    return mock_response\n",
                f"{indent}except Exception as cli_err:\n",
                f'{indent}    logger.warning("CLI engine failed: %s - falling back to API", cli_err)\n',
                f"\n",
                f"{indent}# FALLBACK: Anthropic API\n",
                f"{indent}try:\n",
                f"{indent}    kwargs = dict(\n",
                f"{indent}        model=use_model,\n",
                f"{indent}        max_tokens=MAX_TOKENS,\n",
                f"{indent}        system=system_blocks,\n",
                f"{indent}        messages=managed_messages,\n",
                f"{indent}    )\n",
                f"{indent}    if use_tools:\n",
                f"{indent}        if use_tools is self.orchestrator_tools:\n",
                f'{indent}            kwargs["tools"] = self._cached_orchestrator_tools\n',
                f"{indent}        else:\n",
                f"{indent}            cached_tools = [t.copy() for t in use_tools]\n",
                f"{indent}            if cached_tools:\n",
                f'{indent}                cached_tools[-1] = {{**cached_tools[-1], "cache_control": {{"type": "ephemeral"}}}}\n',
                f'{indent}            kwargs["tools"] = cached_tools\n',
                f"{indent}    if thinking_budget > 0:\n",
                f'{indent}        kwargs["thinking"] = {{"type": "enabled", "budget_tokens": thinking_budget}}\n',
                f'{indent}        kwargs["max_tokens"] = max(MAX_TOKENS, thinking_budget + 4096)\n',
                f"{indent}    return self.client.messages.create(**kwargs)\n",
            ]
            new_lines.extend(cli_block)
            inserted = True
            continue

    if not skip_until_except:
        new_lines.append(line)

with open(filepath, "w") as f:
    f.writelines(new_lines)

print("PATCHED OK" if inserted else "PATCH FAILED - pattern not found")
