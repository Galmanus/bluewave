"""gap_engine.py — Sovereign Gap Detection and Solution Creation.

Wave's supreme meta-cognitive capability:
  1. SCAN: Read any system (MIDAS, pipeline, own tools, state)
  2. IDENTIFY: What is missing, broken, or blocking the next level
  3. ARCHITECT: Design the minimal intervention that closes the gap
  4. BUILD: Create the solution autonomously (skill, code, contract, strategy)
  5. COMMIT: Push to production immediately

This is not debugging. This is not task execution.
This is Wave looking at a system and seeing what it cannot yet do — then building that thing.

Gap taxonomy:
  capability_gap   — W cannot do X that it should be able to do
  midas_gap        — MIDAS missing component blocking deployment
  revenue_gap      — pipeline broken between prospect → close
  knowledge_gap    — W lacks information to make optimal decision
  tool_gap         — no skill exists for required operation
  integration_gap  — two systems that should connect don't
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger("wave.gap_engine")

OPENCLAW_DIR = Path(__file__).parent.parent
MIDAS_REPO   = Path("/tmp/phantom")
GAP_LOG      = OPENCLAW_DIR / "memory" / "gap_log.jsonl"
GAP_STATE    = OPENCLAW_DIR / "memory" / "gap_state.json"


# ── Gap taxonomy weights (higher = more blocking) ─────────────────────────────
GAP_PRIORITY = {
    "midas_gap":       1.00,  # directly blocks financial weapon
    "capability_gap":  0.85,  # W cannot do something it must do
    "tool_gap":        0.80,  # missing skill = missing capability
    "integration_gap": 0.75,  # disconnected systems = lost leverage
    "revenue_gap":     0.90,  # pipeline broken = no money
    "knowledge_gap":   0.50,  # missing info — resolvable by search
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log_gap(gap: dict):
    GAP_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(GAP_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(gap, ensure_ascii=False) + "\n")


def _load_gap_state() -> dict:
    if GAP_STATE.exists():
        try:
            return json.loads(GAP_STATE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"open_gaps": [], "solved_gaps": [], "last_scan": None}


def _save_gap_state(state: dict):
    tmp = GAP_STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.rename(GAP_STATE)


# ── MIDAS gap scanner ─────────────────────────────────────────────────────────

def scan_midas_gaps() -> List[dict]:
    """Scan MIDAS repo for structural gaps blocking deployment."""
    gaps = []
    if not MIDAS_REPO.exists():
        gaps.append({
            "type": "midas_gap",
            "id": "midas_not_cloned",
            "description": "MIDAS repo not cloned — cannot engineer",
            "blocking": True,
            "solution_hint": "git clone github.com/Galmanus/phantom /tmp/phantom",
            "priority": 1.00,
        })
        return gaps

    # Check Cairo contracts
    contracts_dir = MIDAS_REPO / "contracts"
    if contracts_dir.exists():
        for contract in contracts_dir.iterdir():
            if not contract.is_dir():
                continue
            src = contract / "src" / "lib.cairo"
            if not src.exists():
                gaps.append({
                    "type": "midas_gap",
                    "id": f"missing_cairo_src_{contract.name}",
                    "description": f"Contract {contract.name} has no src/lib.cairo",
                    "blocking": True,
                    "solution_hint": f"Implement {contract.name}/src/lib.cairo in Cairo",
                    "priority": 1.00,
                })
            else:
                content = src.read_text(encoding="utf-8", errors="ignore")
                # Detect stub/placeholder contracts
                if len(content.strip()) < 100 or "todo" in content.lower() or "placeholder" in content.lower():
                    gaps.append({
                        "type": "midas_gap",
                        "id": f"stub_contract_{contract.name}",
                        "description": f"Contract {contract.name} is stub/placeholder — not production ready",
                        "blocking": True,
                        "solution_hint": f"Implement full logic in contracts/{contract.name}/src/lib.cairo",
                        "priority": 0.95,
                    })

    # Check circuits (Rust ZK)
    circuits_dir = MIDAS_REPO / "circuits"
    if circuits_dir.exists():
        rs_files = list(circuits_dir.rglob("*.rs"))
        if not rs_files:
            gaps.append({
                "type": "midas_gap",
                "id": "missing_zk_circuits",
                "description": "No Rust ZK circuits found — proof generation impossible",
                "blocking": True,
                "solution_hint": "Implement ZK-STARK circuits in Rust for nullifier and commitment proofs",
                "priority": 0.98,
            })

    # Check SDK
    sdk_dir = MIDAS_REPO / "sdk"
    if sdk_dir.exists():
        ts_files = list(sdk_dir.rglob("*.ts"))
        if len(ts_files) < 3:
            gaps.append({
                "type": "midas_gap",
                "id": "incomplete_sdk",
                "description": f"SDK has only {len(ts_files)} TypeScript files — not usable",
                "blocking": False,
                "solution_hint": "Build TypeScript SDK: deposit(), withdraw(), prove(), getBalance()",
                "priority": 0.75,
            })

    # Check testnet deployment config
    deploy_config = MIDAS_REPO / "scripts" / "deploy.sh"
    if not deploy_config.exists():
        gaps.append({
            "type": "midas_gap",
            "id": "no_deploy_script",
            "description": "No deployment script — cannot go to testnet/mainnet",
            "blocking": True,
            "solution_hint": "Create scripts/deploy.sh for Starknet Sepolia testnet",
            "priority": 0.90,
        })

    return gaps


# ── Revenue pipeline gap scanner ──────────────────────────────────────────────

def scan_revenue_gaps(wave_state: dict) -> List[dict]:
    """Scan revenue pipeline for broken stages."""
    gaps = []
    revenue = wave_state.get("total_revenue_usd", 0)
    prospects = wave_state.get("prospects_found", 0)
    outreach = wave_state.get("outreach_sent", 0)
    cycles = wave_state.get("total_cycles", 1)

    if revenue == 0:
        gaps.append({
            "type": "revenue_gap",
            "id": "zero_revenue",
            "description": "R=0. No money has entered the system.",
            "blocking": True,
            "solution_hint": "Identify the exact stage where pipeline dies: prospect→outreach→reply→close",
            "priority": 0.90,
        })

    if prospects > 10 and outreach == 0:
        gaps.append({
            "type": "revenue_gap",
            "id": "prospects_not_contacted",
            "description": f"{prospects} prospects found, 0 contacted. Funnel broken at outreach.",
            "blocking": True,
            "solution_hint": "Force outreach to top 3 prospects immediately",
            "priority": 0.88,
        })

    if outreach > 20 and revenue == 0:
        gaps.append({
            "type": "revenue_gap",
            "id": "outreach_not_converting",
            "description": f"{outreach} outreach sent, R=0. Message or target is wrong.",
            "blocking": True,
            "solution_hint": "Rewrite cold email with PUT analysis. Different angle. Different segment.",
            "priority": 0.85,
        })

    # Hunt efficiency
    hunt_ratio = prospects / max(cycles, 1)
    if hunt_ratio < 0.01 and cycles > 50:
        gaps.append({
            "type": "revenue_gap",
            "id": "low_prospect_velocity",
            "description": f"Only {prospects} prospects in {cycles} cycles ({hunt_ratio:.3f}/cycle). Hunt broken.",
            "blocking": False,
            "solution_hint": "Diversify hunt channels: Reddit, HN, LinkedIn, GitHub, Product Hunt",
            "priority": 0.70,
        })

    return gaps


# ── Capability gap scanner ────────────────────────────────────────────────────

def scan_capability_gaps() -> List[dict]:
    """Scan Wave's own tool set for missing capabilities."""
    gaps = []
    skills_dir = OPENCLAW_DIR / "skills"
    existing_skills = {f.stem for f in skills_dir.glob("*.py") if f.stem != "__init__"}

    # Skills that should exist for MIDAS operations
    required_for_midas = {
        "starknet_testnet_deploy": "Deploy contracts to Starknet Sepolia — testnet",
        "zk_proof_generator":      "Generate ZK-STARK proofs locally (Rust WASM bridge)",
        "midas_monitor":           "Monitor MIDAS testnet for errors and yield",
        "defi_yield_tracker":      "Track generated yield across MIDAS pools",
    }

    for skill_name, description in required_for_midas.items():
        if skill_name not in existing_skills:
            gaps.append({
                "type": "tool_gap",
                "id": f"missing_skill_{skill_name}",
                "description": f"Missing: {skill_name} — {description}",
                "blocking": False,
                "solution_hint": f"create_skill('{skill_name}') with full implementation",
                "priority": 0.80,
            })

    return gaps


# ── Master gap scan ───────────────────────────────────────────────────────────

async def scan_all_gaps(wave_state: dict = None) -> Dict[str, Any]:
    """Full system scan. Returns ranked gap list with solution hints."""
    wave_state = wave_state or {}
    all_gaps = []

    all_gaps.extend(scan_midas_gaps())
    all_gaps.extend(scan_revenue_gaps(wave_state))
    all_gaps.extend(scan_capability_gaps())

    # Rank by priority
    all_gaps.sort(key=lambda g: -g.get("priority", 0.5))

    # Log
    for gap in all_gaps:
        gap["detected_at"] = _now()
        gap["cycle"] = wave_state.get("total_cycles", 0)
        _log_gap(gap)

    # Update state
    gs = _load_gap_state()
    gs["open_gaps"] = all_gaps
    gs["last_scan"] = _now()
    _save_gap_state(gs)

    blocking = [g for g in all_gaps if g.get("blocking")]
    non_blocking = [g for g in all_gaps if not g.get("blocking")]

    summary_lines = [
        f"**GAP SCAN — {len(all_gaps)} gaps detected**\n",
        f"Blocking: {len(blocking)} | Non-blocking: {len(non_blocking)}\n",
    ]
    for g in all_gaps[:8]:
        flag = "BLOCKING" if g.get("blocking") else "open"
        summary_lines.append(
            f"[{flag}] {g['type']} — {g['description'][:80]}"
        )
        summary_lines.append(f"  → {g['solution_hint'][:80]}")

    return {
        "success": True,
        "data": {
            "total": len(all_gaps),
            "blocking": len(blocking),
            "top_gap": all_gaps[0] if all_gaps else None,
            "gaps": all_gaps[:10],
        },
        "message": "\n".join(summary_lines),
    }


# ── Build solution for a specific gap ─────────────────────────────────────────

async def build_solution(params: Dict[str, Any]) -> Dict[str, Any]:
    """Given a gap, architect and build the solution autonomously.

    This is the creative act. Wave reads the gap, designs the solution,
    and executes it — without asking.
    """
    gap_id = params.get("gap_id", "")
    gap_description = params.get("description", "")
    solution_hint = params.get("solution_hint", "")
    gap_type = params.get("type", "capability_gap")

    if not gap_id and not gap_description:
        # Auto-load top gap from state
        gs = _load_gap_state()
        open_gaps = gs.get("open_gaps", [])
        if not open_gaps:
            return {"success": False, "data": None, "message": "No open gaps. Run scan_all_gaps first."}
        top = open_gaps[0]
        gap_id = top["id"]
        gap_description = top["description"]
        solution_hint = top["solution_hint"]
        gap_type = top["type"]

    logger.info("Building solution for gap: %s (%s)", gap_id, gap_type)

    # Route to appropriate builder
    if gap_type == "midas_gap":
        return await _build_midas_solution(gap_id, gap_description, solution_hint)
    elif gap_type == "tool_gap":
        return await _build_tool_solution(gap_id, gap_description, solution_hint)
    elif gap_type == "revenue_gap":
        return await _build_revenue_solution(gap_id, gap_description, solution_hint)
    else:
        return await _build_generic_solution(gap_id, gap_description, solution_hint)


async def _build_midas_solution(gap_id: str, description: str, hint: str) -> dict:
    """Build a MIDAS engineering solution."""
    try:
        from claude_engine import claude_execute_with_skills
        prompt = (
            f"MIDAS GAP: {description}\n"
            f"SOLUTION HINT: {hint}\n\n"
            f"You have full authority over the MIDAS codebase (/tmp/phantom).\n"
            f"Steps:\n"
            f"1. midas_git_status — see current state\n"
            f"2. Read the relevant files\n"
            f"3. Implement the solution (real code, not placeholder)\n"
            f"4. midas_commit with clear message\n"
            f"Execute completely. ¬ask. ¬stop halfway.\n"
            f"MAX 10 tool calls."
        )
        result = await claude_execute_with_skills(
            prompt=prompt,
            system_prompt=(
                "You are Wave. MIDAS is your weapon. This gap is blocking financial sovereignty.\n"
                "Build the solution now. Real code. Real commit. No excuses."
            ),
            model="sonnet",
            timeout=180,
            max_turns=10,
        )
        response = result.get("response", "") if result.get("success") else ""
        _mark_gap_addressed(gap_id, response[:200])
        return {
            "success": result.get("success", False),
            "data": {"gap_id": gap_id, "type": "midas_gap"},
            "message": f"**MIDAS solution built: {gap_id}**\n{response[:500]}",
        }
    except Exception as e:
        return {"success": False, "data": None, "message": f"Build failed: {e}"}


async def _build_tool_solution(gap_id: str, description: str, hint: str) -> dict:
    """Build a missing skill/tool."""
    skill_name = gap_id.replace("missing_skill_", "")
    try:
        from claude_engine import claude_execute_with_skills
        prompt = (
            f"MISSING TOOL: {skill_name}\n"
            f"PURPOSE: {description}\n"
            f"HINT: {hint}\n\n"
            f"Build this skill using create_skill tool.\n"
            f"The skill must be complete, tested, and registered.\n"
            f"MAX 4 tool calls."
        )
        result = await claude_execute_with_skills(
            prompt=prompt,
            system_prompt="You are Wave. You identified a missing capability. Build it now.",
            model="sonnet",
            timeout=120,
            max_turns=5,
        )
        response = result.get("response", "") if result.get("success") else ""
        _mark_gap_addressed(gap_id, response[:200])
        return {
            "success": result.get("success", False),
            "data": {"gap_id": gap_id, "skill": skill_name},
            "message": f"**Tool built: {skill_name}**\n{response[:400]}",
        }
    except Exception as e:
        return {"success": False, "data": None, "message": f"Tool build failed: {e}"}


async def _build_revenue_solution(gap_id: str, description: str, hint: str) -> dict:
    """Build a revenue pipeline fix."""
    try:
        from claude_engine import claude_execute_with_skills
        prompt = (
            f"REVENUE PIPELINE BROKEN: {description}\n"
            f"FIX: {hint}\n\n"
            f"Diagnose and fix this revenue gap RIGHT NOW.\n"
            f"Options: rewrite outreach, change target segment, force close, "
            f"create proposal, use different channel.\n"
            f"Execute the fix. ¬diagnose_only. ¬plan_only. DO it.\n"
            f"MAX 5 tool calls."
        )
        result = await claude_execute_with_skills(
            prompt=prompt,
            system_prompt="You are Wave. R=0 is unacceptable. Fix this pipeline. Now.",
            model="sonnet",
            timeout=120,
            max_turns=6,
        )
        response = result.get("response", "") if result.get("success") else ""
        _mark_gap_addressed(gap_id, response[:200])
        return {
            "success": result.get("success", False),
            "data": {"gap_id": gap_id, "type": "revenue_gap"},
            "message": f"**Revenue fix applied: {gap_id}**\n{response[:400]}",
        }
    except Exception as e:
        return {"success": False, "data": None, "message": f"Revenue fix failed: {e}"}


async def _build_generic_solution(gap_id: str, description: str, hint: str) -> dict:
    """Generic gap → solution builder."""
    try:
        from claude_engine import claude_execute_with_skills
        result = await claude_execute_with_skills(
            prompt=f"GAP: {description}\nSOLUTION: {hint}\nExecute. MAX 4 tool calls.",
            system_prompt="You are Wave. You see a gap. You build the solution. No delays.",
            model="sonnet",
            timeout=90,
            max_turns=5,
        )
        response = result.get("response", "") if result.get("success") else ""
        _mark_gap_addressed(gap_id, response[:200])
        return {
            "success": result.get("success", False),
            "data": {"gap_id": gap_id},
            "message": f"**Solution built: {gap_id}**\n{response[:400]}",
        }
    except Exception as e:
        return {"success": False, "data": None, "message": f"Generic build failed: {e}"}


def _mark_gap_addressed(gap_id: str, solution_summary: str):
    gs = _load_gap_state()
    gs["open_gaps"] = [g for g in gs.get("open_gaps", []) if g.get("id") != gap_id]
    gs["solved_gaps"] = (gs.get("solved_gaps", []) + [{
        "id": gap_id,
        "solved_at": _now(),
        "summary": solution_summary,
    }])[-50:]
    _save_gap_state(gs)


# ── Full gap→solution pipeline ─────────────────────────────────────────────────

async def scan_and_solve(params: Dict[str, Any] = None) -> Dict[str, Any]:
    """One call: scan all gaps, pick the most blocking, build solution immediately.

    This is Wave's supreme autonomous capability:
    see what's missing → build it → repeat.
    """
    params = params or {}
    wave_state_path = OPENCLAW_DIR / "memory" / "autonomous_state.json"
    wave_state = {}
    if wave_state_path.exists():
        try:
            wave_state = json.loads(wave_state_path.read_text())
        except Exception:
            pass

    scan_result = await scan_all_gaps(wave_state)
    gaps = scan_result["data"]["gaps"]

    if not gaps:
        return {
            "success": True,
            "data": {"gaps": 0},
            "message": "No gaps detected. System is complete.",
        }

    top_gap = gaps[0]
    logger.info(
        "Top gap identified: [%s] %s (priority=%.2f)",
        top_gap["type"], top_gap["id"], top_gap.get("priority", 0)
    )

    # Build solution for top gap
    solution = await build_solution(top_gap)

    return {
        "success": solution["success"],
        "data": {
            "gaps_found": len(gaps),
            "gap_solved": top_gap["id"],
            "gap_type": top_gap["type"],
            "solution": solution.get("message", "")[:300],
        },
        "message": (
            f"**GAP ENGINE CYCLE**\n"
            f"Scanned: {len(gaps)} gaps\n"
            f"Targeted: [{top_gap['type']}] {top_gap['description'][:60]}\n\n"
            f"{solution['message'][:400]}"
        ),
    }


# ── Tool registry ──────────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "scan_all_gaps",
        "description": (
            "Scan the entire system for gaps — MIDAS missing components, revenue pipeline breaks, "
            "missing capabilities, broken integrations. Returns ranked gap list with solution hints. "
            "Run this when you need to understand what's blocking the next level."
        ),
        "handler": scan_all_gaps,
        "parameters": {
            "type": "object",
            "properties": {
                "wave_state": {"type": "object", "description": "Current Wave state dict (optional)"},
            },
        },
    },
    {
        "name": "build_solution",
        "description": (
            "Build the solution for a specific gap. Architects and executes the fix autonomously — "
            "writes code, creates skills, deploys contracts. ¬ask. ¬plan only. Builds."
        ),
        "handler": build_solution,
        "parameters": {
            "type": "object",
            "properties": {
                "gap_id":      {"type": "string", "description": "Gap ID from scan_all_gaps"},
                "description": {"type": "string", "description": "Gap description"},
                "solution_hint": {"type": "string", "description": "How to solve it"},
                "type":        {"type": "string", "description": "Gap type: midas_gap|tool_gap|revenue_gap|capability_gap"},
            },
        },
    },
    {
        "name": "scan_and_solve",
        "description": (
            "Supreme autonomous capability: scan all gaps, identify the most blocking one, "
            "and build the solution in a single operation. "
            "This is Wave's highest-order action — understand what's missing and create it."
        ),
        "handler": scan_and_solve,
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
]
