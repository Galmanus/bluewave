#!/usr/bin/env python3
"""OpenClaw Interactive CLI — talk to the Bluewave agent system.

Usage:
    python cli.py                      # interactive REPL
    python cli.py "list my assets"     # single-shot query
    python cli.py --agent curator "show drafts"  # talk directly to a specialist

Environment:
    ANTHROPIC_API_KEY     — required (Claude API key)
    BLUEWAVE_API_URL      — Bluewave backend URL (default: http://localhost:8300/api/v1)
    BLUEWAVE_API_KEY      — Bluewave API key for authentication
    OPENCLAW_MODEL        — Claude model (default: claude-sonnet-4-20250514)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time

# ── Setup logging before imports ──────────────────────────────

LOG_LEVEL = os.environ.get("OPENCLAW_LOG_LEVEL", "WARNING").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.WARNING),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)

from orchestrator import Orchestrator
from agent_runtime import AgentRuntime, AgentConfig, load_all_tools, load_prompt
from handler import BlueWaveHandler

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.text import Text
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


# ── Display helpers ───────────────────────────────────────────

if HAS_RICH:
    console = Console()

    def print_banner():
        banner = Text()
        banner.append("🌊 ", style="bold cyan")
        banner.append("OpenClaw", style="bold white")
        banner.append(" — Bluewave AI Agent System", style="dim")
        console.print(Panel(banner, border_style="cyan", padding=(0, 2)))
        console.print(
            "  [dim]Fale com Wave, o orquestrador, ou delegue para especialistas.[/dim]"
        )
        console.print(
            "  [dim]Comandos: [bold]/reset[/bold] limpar contexto  "
            "[bold]/agents[/bold] listar agentes  "
            "[bold]/quit[/bold] sair[/dim]"
        )
        console.print()

    def print_response(text, agent_emoji="🌊", agent_name="Wave"):
        console.print()
        label = "%s %s" % (agent_emoji, agent_name)
        try:
            md = Markdown(text)
            console.print(Panel(md, title=label, border_style="cyan", padding=(1, 2)))
        except Exception:
            console.print(Panel(text, title=label, border_style="cyan", padding=(1, 2)))
        console.print()

    def print_thinking():
        console.print("  [dim cyan]⠋ pensando...[/dim cyan]", end="\r")

    def print_error(msg):
        console.print("[bold red]✗[/bold red] %s" % msg)

    def print_info(msg):
        console.print("[dim]%s[/dim]" % msg)

    def get_input():
        try:
            return console.input("[bold cyan]você >[/bold cyan] ")
        except (EOFError, KeyboardInterrupt):
            return None

else:
    def print_banner():
        print("\n🌊 OpenClaw — Bluewave AI Agent System")
        print("  Fale com Wave, o orquestrador, ou delegue para especialistas.")
        print("  Comandos: /reset  /agents  /quit\n")

    def print_response(text, agent_emoji="🌊", agent_name="Wave"):
        print("\n%s %s:\n%s\n" % (agent_emoji, agent_name, text))

    def print_thinking():
        print("  ⠋ pensando...", end="\r")

    def print_error(msg):
        print("✗ %s" % msg)

    def print_info(msg):
        print("  %s" % msg)

    def get_input():
        try:
            return input("você > ")
        except (EOFError, KeyboardInterrupt):
            return None


# ── Agents directory ──────────────────────────────────────────

AGENTS_INFO = {
    "asset-curator":        ("🎨", "Curator",    "Gestão de assets digitais"),
    "workflow-director":    ("✅", "Director",   "Workflow de aprovação"),
    "brand-guardian":       ("🛡️", "Guardian",   "Brand compliance e governança"),
    "analytics-strategist": ("📊", "Strategist", "Analytics e inteligência de dados"),
    "creative-strategist":  ("✍️", "Creative",   "Estratégia de conteúdo"),
    "ops-admin":            ("⚙️", "Admin",      "Administração de plataforma"),
}


def print_agents():
    print_info("Agentes disponíveis:")
    print_info("  🌊 Wave (orchestrator) — roteador principal")
    for aid, (emoji, name, desc) in AGENTS_INFO.items():
        print_info("  %s %s (%s) — %s" % (emoji, name, aid, desc))


# ── Main REPL ─────────────────────────────────────────────────

def validate_env():
    """Check required environment variables."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        print_error("ANTHROPIC_API_KEY não configurada!")
        print_info("export ANTHROPIC_API_KEY='sk-ant-...'")
        return False

    bw_key = os.environ.get("BLUEWAVE_API_KEY", "")
    if not bw_key:
        print_info("⚠ BLUEWAVE_API_KEY não configurada — tools vão falhar")
        print_info("  export BLUEWAVE_API_KEY='bw_...'")

    return True


async def run_repl(orchestrator):
    """Interactive REPL loop."""
    print_banner()

    while True:
        user_input = get_input()

        if user_input is None:
            print_info("\n👋 Até mais!")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        # Commands
        if user_input.lower() in ("/quit", "/exit", "/q"):
            print_info("👋 Até mais!")
            break

        if user_input.lower() == "/reset":
            orchestrator.reset()
            print_info("🔄 Contexto limpo. Nova conversa.")
            continue

        if user_input.lower() == "/agents":
            print_agents()
            continue

        if user_input.lower() == "/help":
            print_info("Comandos:")
            print_info("  /reset   — limpar contexto da conversa")
            print_info("  /agents  — listar agentes disponíveis")
            print_info("  /quit    — sair")
            print_info("  /debug   — toggle debug logging")
            continue

        if user_input.lower() == "/debug":
            current = logging.getLogger("openclaw").level
            if current <= logging.DEBUG:
                logging.getLogger("openclaw").setLevel(logging.WARNING)
                logging.getLogger("openclaw.runtime").setLevel(logging.WARNING)
                logging.getLogger("openclaw.orchestrator").setLevel(logging.WARNING)
                print_info("🔇 Debug desativado")
            else:
                logging.getLogger("openclaw").setLevel(logging.DEBUG)
                logging.getLogger("openclaw.runtime").setLevel(logging.DEBUG)
                logging.getLogger("openclaw.orchestrator").setLevel(logging.DEBUG)
                print_info("🔊 Debug ativado")
            continue

        # Send to orchestrator
        print_thinking()
        t0 = time.time()

        try:
            response = await orchestrator.chat(user_input)
        except KeyboardInterrupt:
            print_info("\n⏹ Interrompido.")
            continue
        except Exception as e:
            print_error("Erro: %s" % str(e))
            continue

        elapsed = time.time() - t0
        print_response(response)
        print_info("  ⏱ %.1fs" % elapsed)


async def run_single(orchestrator, message):
    """Single-shot: send one message and print the response."""
    response = await orchestrator.chat(message)
    print_response(response)


def main():
    parser = argparse.ArgumentParser(
        description="🌊 OpenClaw — Bluewave AI Agent CLI"
    )
    parser.add_argument(
        "message",
        nargs="*",
        help="Single message to send (omit for interactive REPL)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Claude model override",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    if args.debug:
        logging.getLogger("openclaw").setLevel(logging.DEBUG)
        logging.getLogger("openclaw.runtime").setLevel(logging.DEBUG)
        logging.getLogger("openclaw.orchestrator").setLevel(logging.DEBUG)

    if not validate_env():
        sys.exit(1)

    # Initialize
    print_info("Inicializando agentes...")
    try:
        handler = BlueWaveHandler()
    except ValueError:
        handler = None

    if handler is None:
        print_info("⚠ BlueWaveHandler não inicializado (sem BLUEWAVE_API_KEY)")
        print_info("  O agente vai funcionar, mas chamadas de tool vão falhar.")
        # Create a dummy handler for testing
        handler = BlueWaveHandler.__new__(BlueWaveHandler)
        handler.api_url = os.environ.get("BLUEWAVE_API_URL", "http://localhost:8300/api/v1")

    orchestrator = Orchestrator(
        handler=handler,
        model=args.model,
    )

    message = " ".join(args.message) if args.message else None

    if message:
        asyncio.run(run_single(orchestrator, message))
    else:
        asyncio.run(run_repl(orchestrator))


if __name__ == "__main__":
    main()
