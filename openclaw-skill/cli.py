#!/usr/bin/env python3
"""OpenClaw Interactive CLI — talk to the Bluewave agent system (Gemini Edition).

Usage:
    python cli.py                      # interactive REPL
    python cli.py "list my assets"     # single-shot query

Environment:
    GEMINI_API_KEY        — required (Gemini API key)
    BLUEWAVE_API_URL      — Bluewave backend URL
    BLUEWAVE_API_KEY      — Bluewave API key
    OPENCLAW_MODEL        — Gemini model (default: gemini-2.0-flash)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time

from orchestrator import Orchestrator
from handler import BlueWaveHandler

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.text import Text
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

if HAS_RICH:
    console = Console()
    def print_banner():
        banner = Text("🌊 OpenClaw — Gemini Sovereign Engine", style="bold cyan")
        console.print(Panel(banner, border_style="cyan"))
    def print_response(text, name="Wave"):
        console.print(Panel(Markdown(text), title=name, border_style="cyan"))
    def print_thinking(): console.print("  [dim]pensando...[/dim]", end="\r")
    def print_error(msg): console.print(f"[red]✗ {msg}[/red]")
    def print_info(msg): console.print(f"[dim]{msg}[/dim]")
    def get_input(): return console.input("[bold cyan]você > [/bold cyan]")
else:
    def print_banner(): print("\n🌊 OpenClaw (Gemini Edition)")
    def print_response(text, name="Wave"): print(f"\n{name}:\n{text}\n")
    def print_thinking(): print("  pensando...", end="\r")
    def print_error(msg): print(f"✗ {msg}")
    def print_info(msg): print(f"  {msg}")
    def get_input(): return input("você > ")

def validate_env():
    if not os.environ.get("GEMINI_API_KEY"):
        print_error("GEMINI_API_KEY não configurada!")
        return False
    return True

async def run_repl(orch):
    print_banner()
    while True:
        try:
            inp = get_input().strip()
            if inp.lower() in ["/quit", "/exit"]: break
            if inp.lower() == "/reset":
                orch.history = []
                print_info("Contexto limpo.")
                continue
            print_thinking()
            resp = await orch.chat(inp)
            print_response(resp)
        except (EOFError, KeyboardInterrupt): break

def main():
    if not validate_env(): sys.exit(1)
    try:
        handler = BlueWaveHandler()
    except:
        handler = None
    orch = Orchestrator(handler=handler)
    asyncio.run(run_repl(orch))

if __name__ == "__main__":
    main()
