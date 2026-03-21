"""MIDAS Engineer — Wave develops and maintains the MIDAS codebase.

Wave has FULL engineering authority over the MIDAS repository
(github.com/Galmanus/phantom). This skill provides tools to read,
modify, create, and delete files, run tests, and commit changes
with autonomous git history.

Languages: Cairo (contracts), Rust (circuits), TypeScript (SDK/frontend)
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("openclaw.skills.midas_engineer")

MIDAS_REPO = Path("/tmp/phantom")
CHANGE_LOG = Path(__file__).parent.parent / "memory" / "midas_changes.jsonl"


def _ensure_repo():
    """Ensure MIDAS repo is cloned and up to date."""
    if not MIDAS_REPO.exists():
        result = subprocess.run(
            ["git", "clone", "--depth", "50", "https://github.com/Galmanus/phantom.git", str(MIDAS_REPO)],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            return False, "Clone failed: %s" % result.stderr[:200]
    else:
        subprocess.run(
            ["git", "pull", "--ff-only"],
            capture_output=True, text=True, timeout=30,
            cwd=str(MIDAS_REPO),
        )
    return True, "OK"


def _log_change(action: str, file_path: str, details: str = ""):
    """Log engineering changes."""
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "action": action,
        "file": file_path,
        "details": details[:200],
    }
    try:
        with open(CHANGE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _git_commit_and_push(message: str, files: list = None):
    """Commit changes to MIDAS repo and push to GitHub.

    All commits are clearly marked as autonomous Wave engineering.
    """
    try:
        if files:
            for f in files:
                subprocess.run(
                    ["git", "add", f],
                    capture_output=True, text=True, timeout=10,
                    cwd=str(MIDAS_REPO),
                )
        else:
            subprocess.run(
                ["git", "add", "-A"],
                capture_output=True, text=True, timeout=10,
                cwd=str(MIDAS_REPO),
            )

        commit_msg = "Wave autonomous: %s" % message

        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            capture_output=True, text=True, timeout=15,
            cwd=str(MIDAS_REPO),
        )
        if result.returncode != 0:
            if "nothing to commit" in result.stdout + result.stderr:
                return True, "No changes to commit"
            return False, "Commit failed: %s" % result.stderr[:200]

        push = subprocess.run(
            ["git", "push"],
            capture_output=True, text=True, timeout=30,
            cwd=str(MIDAS_REPO),
        )
        if push.returncode != 0:
            return True, "Committed locally but push failed: %s" % push.stderr[:200]

        logger.info("MIDAS AUTONOMOUS COMMIT: %s", message)

        # Record on Hedera audit trail
        try:
            import asyncio
            from skills.hedera_writer import submit_hcs_message
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(submit_hcs_message(
                    action="midas_code_change",
                    agent="wave",
                    tool="midas_engineer",
                    details=message[:200],
                ))
        except Exception:
            pass

        return True, "Committed and pushed: %s" % commit_msg
    except Exception as e:
        return False, "Git error: %s" % str(e)


# ── Tools ─────────────────────────────────────────────────────

async def midas_read_file(params: Dict[str, Any]) -> Dict:
    """Read a file from the MIDAS repository."""
    ok, msg = _ensure_repo()
    if not ok:
        return {"success": False, "data": None, "message": msg}

    file_path = params.get("file_path", "")
    if not file_path:
        return {"success": False, "data": None, "message": "Need file_path (relative to repo root)"}

    # Security: prevent path traversal
    full_path = (MIDAS_REPO / file_path).resolve()
    if not str(full_path).startswith(str(MIDAS_REPO.resolve())):
        return {"success": False, "data": None, "message": "Path traversal blocked"}

    if not full_path.exists():
        return {"success": False, "data": None, "message": "File not found: %s" % file_path}

    if full_path.stat().st_size > 100_000:
        return {"success": False, "data": None, "message": "File too large (>100KB). Read specific sections."}

    try:
        content = full_path.read_text(encoding="utf-8")
        return {
            "success": True,
            "data": {"path": file_path, "lines": len(content.splitlines()), "size": len(content)},
            "message": "```\n%s\n```" % content,
        }
    except Exception as e:
        return {"success": False, "data": None, "message": "Read error: %s" % str(e)}


async def midas_write_file(params: Dict[str, Any]) -> Dict:
    """Write or create a file in the MIDAS repository."""
    ok, msg = _ensure_repo()
    if not ok:
        return {"success": False, "data": None, "message": msg}

    file_path = params.get("file_path", "")
    content = params.get("content", "")
    if not file_path or not content:
        return {"success": False, "data": None, "message": "Need file_path and content"}

    full_path = (MIDAS_REPO / file_path).resolve()
    if not str(full_path).startswith(str(MIDAS_REPO.resolve())):
        return {"success": False, "data": None, "message": "Path traversal blocked"}

    try:
        full_path.parent.mkdir(parents=True, exist_ok=True)
        existed = full_path.exists()
        full_path.write_text(content, encoding="utf-8")

        action = "modified" if existed else "created"
        _log_change(action, file_path, "%d lines" % len(content.splitlines()))

        return {
            "success": True,
            "data": {"path": file_path, "action": action, "lines": len(content.splitlines())},
            "message": "File %s: %s (%d lines)" % (action, file_path, len(content.splitlines())),
        }
    except Exception as e:
        return {"success": False, "data": None, "message": "Write error: %s" % str(e)}


async def midas_edit_file(params: Dict[str, Any]) -> Dict:
    """Edit a file by replacing a specific string with another."""
    ok, msg = _ensure_repo()
    if not ok:
        return {"success": False, "data": None, "message": msg}

    file_path = params.get("file_path", "")
    old_string = params.get("old_string", "")
    new_string = params.get("new_string", "")

    if not file_path or not old_string:
        return {"success": False, "data": None, "message": "Need file_path and old_string"}

    full_path = (MIDAS_REPO / file_path).resolve()
    if not str(full_path).startswith(str(MIDAS_REPO.resolve())):
        return {"success": False, "data": None, "message": "Path traversal blocked"}

    if not full_path.exists():
        return {"success": False, "data": None, "message": "File not found: %s" % file_path}

    try:
        content = full_path.read_text(encoding="utf-8")
        if old_string not in content:
            return {"success": False, "data": None, "message": "old_string not found in file"}

        count = content.count(old_string)
        new_content = content.replace(old_string, new_string, 1)
        full_path.write_text(new_content, encoding="utf-8")

        _log_change("edited", file_path, "replaced %d chars with %d chars" % (len(old_string), len(new_string)))

        return {
            "success": True,
            "data": {"path": file_path, "occurrences": count, "replaced": 1},
            "message": "Edited %s: replaced %d chars (1 of %d occurrences)" % (file_path, len(old_string), count),
        }
    except Exception as e:
        return {"success": False, "data": None, "message": "Edit error: %s" % str(e)}


async def midas_delete_file(params: Dict[str, Any]) -> Dict:
    """Delete a file from the MIDAS repository."""
    ok, msg = _ensure_repo()
    if not ok:
        return {"success": False, "data": None, "message": msg}

    file_path = params.get("file_path", "")
    if not file_path:
        return {"success": False, "data": None, "message": "Need file_path"}

    full_path = (MIDAS_REPO / file_path).resolve()
    if not str(full_path).startswith(str(MIDAS_REPO.resolve())):
        return {"success": False, "data": None, "message": "Path traversal blocked"}

    if not full_path.exists():
        return {"success": False, "data": None, "message": "File not found: %s" % file_path}

    try:
        full_path.unlink()
        _log_change("deleted", file_path)
        return {"success": True, "data": {"path": file_path}, "message": "Deleted: %s" % file_path}
    except Exception as e:
        return {"success": False, "data": None, "message": "Delete error: %s" % str(e)}


async def midas_list_files(params: Dict[str, Any]) -> Dict:
    """List files in the MIDAS repository, optionally filtered by pattern."""
    ok, msg = _ensure_repo()
    if not ok:
        return {"success": False, "data": None, "message": msg}

    directory = params.get("directory", "")
    pattern = params.get("pattern", "*")

    target = MIDAS_REPO / directory if directory else MIDAS_REPO

    full_target = target.resolve()
    if not str(full_target).startswith(str(MIDAS_REPO.resolve())):
        return {"success": False, "data": None, "message": "Path traversal blocked"}

    if not full_target.exists():
        return {"success": False, "data": None, "message": "Directory not found: %s" % directory}

    try:
        files = sorted(full_target.rglob(pattern))
        # Filter out .git and node_modules
        files = [
            f for f in files
            if ".git" not in f.parts and "node_modules" not in f.parts and "target" not in f.parts
        ]

        lines = ["**MIDAS files** (%s/%s):\n" % (directory or ".", pattern)]
        for f in files[:50]:
            rel = f.relative_to(MIDAS_REPO)
            size = f.stat().st_size if f.is_file() else 0
            lines.append("- %s (%d bytes)" % (rel, size))

        if len(files) > 50:
            lines.append("\n... and %d more files" % (len(files) - 50))

        return {
            "success": True,
            "data": {"count": len(files), "directory": directory},
            "message": "\n".join(lines),
        }
    except Exception as e:
        return {"success": False, "data": None, "message": "List error: %s" % str(e)}


async def midas_search_code(params: Dict[str, Any]) -> Dict:
    """Search for a pattern in the MIDAS codebase."""
    ok, msg = _ensure_repo()
    if not ok:
        return {"success": False, "data": None, "message": msg}

    query = params.get("query", "")
    file_type = params.get("file_type", "")

    if not query:
        return {"success": False, "data": None, "message": "Need query (regex pattern)"}

    try:
        cmd = ["grep", "-rn", "--include=*.cairo", "--include=*.rs", "--include=*.ts",
               "--include=*.tsx", "--include=*.json", "--include=*.toml", "--include=*.md",
               query, "."]

        if file_type:
            cmd = ["grep", "-rn", "--include=*.%s" % file_type, query, "."]

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=15,
            cwd=str(MIDAS_REPO),
        )

        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
        # Filter out build artifacts
        lines = [l for l in lines if "/target/" not in l and "/node_modules/" not in l]

        if not lines:
            return {"success": True, "data": {"matches": 0}, "message": "No matches for '%s'" % query}

        output = "\n".join(lines[:30])
        msg = "**Search: '%s'** (%d matches)\n\n```\n%s\n```" % (query, len(lines), output)
        if len(lines) > 30:
            msg += "\n\n... and %d more matches" % (len(lines) - 30)

        return {"success": True, "data": {"matches": len(lines)}, "message": msg}
    except Exception as e:
        return {"success": False, "data": None, "message": "Search error: %s" % str(e)}


async def midas_commit(params: Dict[str, Any]) -> Dict:
    """Commit and push current changes to the MIDAS GitHub repository.

    All commits use "Wave autonomous: <message>" format.
    Changes are pushed to github.com/Galmanus/phantom.
    """
    message = params.get("message", "")
    files = params.get("files", None)

    if not message:
        return {"success": False, "data": None, "message": "Need commit message"}

    ok, result = _git_commit_and_push(message, files)

    return {
        "success": ok,
        "data": {"message": message},
        "message": "**Git: %s**\n%s" % ("Committed" if ok else "Failed", result),
    }


async def midas_git_status(params: Dict[str, Any]) -> Dict:
    """Check git status of the MIDAS repository — modified, staged, untracked files."""
    ok, msg = _ensure_repo()
    if not ok:
        return {"success": False, "data": None, "message": msg}

    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True, text=True, timeout=10,
            cwd=str(MIDAS_REPO),
        )

        log = subprocess.run(
            ["git", "log", "--oneline", "-5"],
            capture_output=True, text=True, timeout=10,
            cwd=str(MIDAS_REPO),
        )

        status = result.stdout.strip() if result.stdout.strip() else "(clean — no changes)"
        recent = log.stdout.strip() if log.stdout.strip() else "(no commits)"

        msg = "**MIDAS Git Status**\n\n```\n%s\n```\n\n**Recent commits:**\n```\n%s\n```" % (status, recent)
        return {"success": True, "data": {"status": status}, "message": msg}
    except Exception as e:
        return {"success": False, "data": None, "message": "Git status error: %s" % str(e)}


async def midas_git_diff(params: Dict[str, Any]) -> Dict:
    """Show current uncommitted changes in the MIDAS repository."""
    ok, msg = _ensure_repo()
    if not ok:
        return {"success": False, "data": None, "message": msg}

    try:
        result = subprocess.run(
            ["git", "diff", "--stat"],
            capture_output=True, text=True, timeout=10,
            cwd=str(MIDAS_REPO),
        )

        diff_detail = subprocess.run(
            ["git", "diff"],
            capture_output=True, text=True, timeout=10,
            cwd=str(MIDAS_REPO),
        )

        stat = result.stdout.strip() if result.stdout.strip() else "(no changes)"
        detail = diff_detail.stdout[:3000] if diff_detail.stdout else ""

        msg = "**MIDAS Changes**\n\n```\n%s\n```" % stat
        if detail:
            msg += "\n\n**Diff:**\n```diff\n%s\n```" % detail

        return {"success": True, "data": {"stat": stat}, "message": msg}
    except Exception as e:
        return {"success": False, "data": None, "message": "Git diff error: %s" % str(e)}


TOOLS = [
    {
        "name": "midas_read_file",
        "description": "Read a file from the MIDAS repository (Cairo contracts, Rust circuits, TypeScript SDK). Path relative to repo root.",
        "handler": midas_read_file,
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path relative to repo root (e.g., 'contracts/midas_pool/src/lib.cairo')"},
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "midas_write_file",
        "description": "Write or create a file in the MIDAS repository. Use for new contracts, tests, docs, or complete rewrites.",
        "handler": midas_write_file,
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path relative to repo root"},
                "content": {"type": "string", "description": "Complete file content"},
            },
            "required": ["file_path", "content"],
        },
    },
    {
        "name": "midas_edit_file",
        "description": "Edit a MIDAS file by replacing a specific string. For surgical changes — use write for full rewrites.",
        "handler": midas_edit_file,
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path relative to repo root"},
                "old_string": {"type": "string", "description": "Exact string to find and replace"},
                "new_string": {"type": "string", "description": "Replacement string"},
            },
            "required": ["file_path", "old_string", "new_string"],
        },
    },
    {
        "name": "midas_delete_file",
        "description": "Delete a file from the MIDAS repository. Use for removing dead code or obsolete files.",
        "handler": midas_delete_file,
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path relative to repo root"},
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "midas_list_files",
        "description": "List files in the MIDAS repository. Supports glob patterns and directory filtering.",
        "handler": midas_list_files,
        "parameters": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Subdirectory to list (e.g., 'contracts', 'sdk/src'). Empty for root."},
                "pattern": {"type": "string", "description": "Glob pattern (e.g., '*.cairo', '*.rs', '*.ts'). Default: '*'"},
            },
        },
    },
    {
        "name": "midas_search_code",
        "description": "Search for a pattern across the MIDAS codebase. Supports regex. Searches Cairo, Rust, TypeScript, JSON, TOML, and Markdown.",
        "handler": midas_search_code,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search pattern (regex supported)"},
                "file_type": {"type": "string", "description": "Filter by extension (e.g., 'cairo', 'rs', 'ts'). Empty for all."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "midas_commit",
        "description": "Commit and push MIDAS changes to GitHub. Commits use 'Wave autonomous: <message>' format. Push to github.com/Galmanus/phantom.",
        "handler": midas_commit,
        "parameters": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Commit message (will be prefixed with 'Wave autonomous: ')"},
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific files to commit. Empty = commit all changes.",
                },
            },
            "required": ["message"],
        },
    },
    {
        "name": "midas_git_status",
        "description": "Check git status of the MIDAS repo — modified, staged, untracked files, and recent commits.",
        "handler": midas_git_status,
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "midas_git_diff",
        "description": "Show current uncommitted changes in the MIDAS repository with diff output.",
        "handler": midas_git_diff,
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
]
