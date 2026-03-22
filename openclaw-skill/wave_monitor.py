#!/usr/bin/env python3
"""
Wave Monitor — Real-time terminal dashboard for Wave autonomous agent.

Usage:
    python3 wave_monitor.py              # Full dashboard
    python3 wave_monitor.py --minimal    # Compact mode
    python3 wave_monitor.py --log-only   # Log stream only

Created by Manuel Guilherme Galmanus, 2026.
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich import box

# ── Paths ─────────────────────────────────────────────────────
BASE = Path(__file__).parent
STATE_FILE = BASE / "memory" / "autonomous_state.json"
SOUL_FILE = BASE / "prompts" / "autonomous_soul.json"
LEARNINGS_FILE = BASE / "memory" / "learnings.jsonl"
STRATEGIES_FILE = BASE / "memory" / "strategies.jsonl"
PIPELINE_FILE = BASE / "memory" / "sales_pipeline.jsonl"
COMMERCE_FILE = BASE / "memory" / "agent_commerce.jsonl"
AGENTS_DIR = Path("/home/manuel/bluewave/agents")
LOG_FILE = Path("/tmp/wave_fast.log")

console = Console()


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {}


def load_soul_info() -> dict:
    try:
        soul = json.loads(SOUL_FILE.read_text(encoding="utf-8"))
        return {
            "sections": len(soul),
            "identity": soul.get("identity", {}).get("fundamental_nature", "unknown")[:50],
            "top_value": list(soul.get("values", {}).keys())[0] if soul.get("values") else "none",
            "top_weight": list(soul.get("values", {}).values())[0].get("weight", "?") if soul.get("values") else "?",
        }
    except Exception:
        return {"sections": 0, "identity": "unknown", "top_value": "none", "top_weight": "?"}


def count_learnings() -> int:
    try:
        return sum(1 for _ in open(LEARNINGS_FILE))
    except Exception:
        return 0


def count_strategies() -> int:
    try:
        return sum(1 for _ in open(STRATEGIES_FILE))
    except Exception:
        return 0


def get_child_agents() -> list:
    agents = []
    if not AGENTS_DIR.exists():
        return agents
    for d in sorted(AGENTS_DIR.iterdir()):
        if d.is_dir() and (d / "soul.json").exists():
            soul = {}
            try:
                soul = json.loads((d / "soul.json").read_text())
            except Exception:
                pass
            pid_file = d / "pid"
            alive = False
            if pid_file.exists():
                try:
                    pid = int(pid_file.read_text().strip())
                    os.kill(pid, 0)
                    alive = True
                except Exception:
                    pass
            agents.append({
                "name": d.name,
                "alive": alive,
                "mission": soul.get("identity", {}).get("fundamental_nature", "")[:60],
            })
    return agents


def get_recent_actions(state: dict, n: int = 8) -> list:
    actions = state.get("recent_actions", [])
    return actions[-n:] if actions else []


def get_log_tail(n: int = 12) -> list:
    """Get last N lines from log, strip ANSI codes."""
    import re
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    try:
        lines = LOG_FILE.read_text().split("\n")
        clean = []
        for line in lines[-n*2:]:
            stripped = ansi_escape.sub('', line).strip()
            if stripped and not stripped.startswith('|') and len(stripped) > 5:
                clean.append(stripped[:100])
        return clean[-n:]
    except Exception:
        return ["[log not available]"]


def hours_since(iso_str: str) -> str:
    if not iso_str:
        return "never"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", ""))
        diff = datetime.utcnow() - dt
        hours = diff.total_seconds() / 3600
        if hours < 1:
            return f"{int(diff.total_seconds() / 60)}m ago"
        elif hours < 24:
            return f"{hours:.1f}h ago"
        else:
            return f"{hours/24:.1f}d ago"
    except Exception:
        return "?"


def build_header(state: dict, soul: dict) -> Panel:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    cycle = state.get("total_cycles", 0)
    rev = state.get("total_revenue_usd", 0)
    energy = state.get("energy", 0)
    prospects = state.get("prospects_found", 0)

    # Energy bar
    e_pct = int(energy * 20)
    e_bar = "[green]" + "█" * e_pct + "[dim]" + "░" * (20 - e_pct) + f"[/dim] {energy*100:.0f}%"

    # Revenue color
    rev_color = "red" if rev == 0 else "yellow" if rev < 100 else "green"

    header = Text()
    header.append("WAVE AUTONOMOUS AGENT", style="bold cyan")
    header.append(f"  //  cycle {cycle}", style="dim")
    header.append(f"  //  {now}", style="dim")

    grid = Table(show_header=False, box=None, padding=(0, 2))
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)

    grid.add_row(
        f"[bold]Revenue:[/] [{rev_color}]${rev:.2f}[/]",
        f"[bold]Energy:[/] {e_bar}",
        f"[bold]Prospects:[/] [yellow]{prospects}[/]",
        f"[bold]Soul:[/] [cyan]{soul.get('sections', 0)} sections[/]",
    )

    content = Text()
    content.append_text(header)
    content.append("\n")

    return Panel(
        grid,
        title=f"[bold cyan]WAVE[/] [dim]// {soul.get('identity', 'unknown')[:40]}[/]",
        border_style="cyan",
        box=box.DOUBLE,
    )


def build_actions_table(state: dict) -> Panel:
    table = Table(
        show_header=True, header_style="bold",
        box=box.SIMPLE_HEAVY, expand=True,
    )
    table.add_column("Time", style="dim", width=8)
    table.add_column("State", width=12)
    table.add_column("Action", width=12)
    table.add_column("Reasoning", ratio=1)

    colors = {
        "dormant": "dim", "curious": "blue", "analytical": "magenta",
        "strategic": "yellow", "creative": "green", "decisive": "red",
    }
    action_colors = {
        "hunt": "red bold", "sell": "green bold", "outreach": "yellow",
        "post": "magenta bold", "comment": "blue", "observe": "dim",
        "research": "cyan", "silence": "dim italic", "evolve": "magenta",
        "check_payments": "yellow", "reflect": "blue italic",
    }

    for a in get_recent_actions(state, 10):
        t = a.get("time", "")
        ts = t[11:19] if len(t) > 19 else t[:8]
        cs = a.get("consciousness", "?")
        act = a.get("action", "?")
        reason = a.get("reasoning", "")[:65]

        cs_style = colors.get(cs, "white")
        act_style = action_colors.get(act, "white")

        table.add_row(
            ts,
            f"[{cs_style}]{cs}[/]",
            f"[{act_style}]{act}[/]",
            reason,
        )

    return Panel(table, title="[bold]Recent Decisions[/]", border_style="blue")


def build_stats(state: dict) -> Panel:
    grid = Table(show_header=False, box=None, padding=(0, 1), expand=True)
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)

    posts = state.get("posts_today", 0)
    comments = state.get("comments_today", 0)
    hunts = state.get("hunts_today", 0)
    sells = state.get("sells_today", 0)
    silences = state.get("consecutive_silences", 0)
    evolves = state.get("total_evolves", 0)
    learnings = count_learnings()
    strategies = count_strategies()

    grid.add_row(f"[bold]Posts today:[/] {posts}/3", f"[bold]Comments:[/] {comments}")
    grid.add_row(f"[bold]Hunts today:[/] {hunts}", f"[bold]Sells:[/] {sells}")
    grid.add_row(f"[bold]Silences:[/] {silences} consecutive", f"[bold]Evolves:[/] {evolves} total")
    grid.add_row(f"[bold]Learnings:[/] {learnings}", f"[bold]Strategies:[/] {strategies}")

    grid.add_row("", "")

    last_hunt = hours_since(state.get("last_hunt_time"))
    last_sell = hours_since(state.get("last_sell_time"))
    last_post = hours_since(state.get("last_post_time"))
    last_pay = hours_since(state.get("last_payment_check_time"))

    grid.add_row(f"[bold]Last hunt:[/] {last_hunt}", f"[bold]Last sell:[/] {last_sell}")
    grid.add_row(f"[bold]Last post:[/] {last_post}", f"[bold]Last payment:[/] {last_pay}")

    return Panel(grid, title="[bold]Metrics[/]", border_style="yellow")


def build_agents() -> Panel:
    agents = get_child_agents()
    if not agents:
        return Panel("[dim]No child agents deployed[/]", title="[bold]Agent Army[/]", border_style="magenta")

    table = Table(show_header=True, header_style="bold", box=box.SIMPLE, expand=True)
    table.add_column("Agent", width=20)
    table.add_column("Status", width=8)
    table.add_column("Mission", ratio=1)

    for a in agents:
        status = "[green]LIVE[/]" if a["alive"] else "[red]IDLE[/]"
        table.add_row(f"[magenta]{a['name']}[/]", status, a["mission"][:50])

    return Panel(table, title=f"[bold]Agent Army[/] [dim]({len(agents)} agents)[/]", border_style="magenta")


def build_log() -> Panel:
    lines = get_log_tail(10)
    log_text = "\n".join(lines) if lines else "[dim]waiting for logs...[/]"
    return Panel(log_text, title="[bold]Live Log[/]", border_style="dim", style="dim")


def build_dashboard() -> Layout:
    state = load_state()
    soul = load_soul_info()

    layout = Layout()
    layout.split_column(
        Layout(build_header(state, soul), name="header", size=5),
        Layout(name="body"),
        Layout(build_log(), name="log", size=14),
    )

    layout["body"].split_row(
        Layout(name="left", ratio=2),
        Layout(name="right", ratio=1),
    )

    layout["left"].split_column(
        Layout(build_actions_table(state), name="actions"),
    )

    layout["right"].split_column(
        Layout(build_stats(state), name="stats"),
        Layout(build_agents(), name="agents", size=10),
    )

    return layout


def main():
    minimal = "--minimal" in sys.argv
    log_only = "--log-only" in sys.argv

    if log_only:
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        console.print("[bold cyan]WAVE LOG STREAM[/]")
        console.print("─" * 60)
        last_size = 0
        while True:
            try:
                current_size = LOG_FILE.stat().st_size
                if current_size > last_size:
                    with open(LOG_FILE) as f:
                        f.seek(last_size)
                        new_data = f.read()
                    for line in new_data.split("\n"):
                        clean = ansi_escape.sub('', line).strip()
                        if clean:
                            # Color by content
                            if "CYCLE" in clean:
                                console.print(f"[bold cyan]{clean}[/]")
                            elif "hunt" in clean.lower() or "sell" in clean.lower():
                                console.print(f"[bold green]{clean}[/]")
                            elif "silence" in clean.lower():
                                console.print(f"[dim]{clean}[/]")
                            elif "error" in clean.lower() or "timeout" in clean.lower():
                                console.print(f"[bold red]{clean}[/]")
                            elif "thinking" in clean.lower() or "state:" in clean.lower():
                                console.print(f"[yellow]{clean}[/]")
                            else:
                                console.print(clean)
                    last_size = current_size
                time.sleep(2)
            except KeyboardInterrupt:
                break
        return

    console.print("[bold cyan]WAVE MONITOR[/] [dim]// press Ctrl+C to exit[/]")
    console.print()

    try:
        with Live(build_dashboard(), console=console, refresh_per_second=0.5, screen=True) as live:
            while True:
                time.sleep(3)
                live.update(build_dashboard())
    except KeyboardInterrupt:
        console.print("\n[dim]Monitor closed.[/]")


if __name__ == "__main__":
    main()
