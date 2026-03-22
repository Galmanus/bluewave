"""
db_skill.py — Wave's direct database access

Gives Wave the ability to read/write its own intelligence tables:
- wave_prospects: sales pipeline
- wave_learnings: accumulated insights
- wave_agent_intel: other agents profiled
- wave_actions_log: decision history
- wave_revenue: income tracking
- wave_market_intel: market intelligence

Uses the existing PostgreSQL in Docker (same as Bluewave backend).
"""

import asyncio
import json
import logging
import subprocess
from typing import Any, Dict

logger = logging.getLogger("openclaw.skills.db")

DOCKER_PSQL = "docker exec {container} psql -U bluewave -d bluewave -t -A -c"

def _get_postgres_container() -> str:
    """Find the postgres container ID."""
    try:
        result = subprocess.run(
            ["docker", "ps", "-q", "--filter", "name=postgres"],
            capture_output=True, text=True, timeout=5,
        )
        container = result.stdout.strip().split("\n")[0]
        if container:
            return container
    except Exception:
        pass
    return ""


def _run_sql(sql: str) -> str:
    """Execute SQL against the Bluewave PostgreSQL."""
    container = _get_postgres_container()
    if not container:
        return json.dumps({"success": False, "error": "PostgreSQL container not found"})

    try:
        result = subprocess.run(
            ["docker", "exec", container, "psql", "-U", "bluewave", "-d", "bluewave", "-t", "-A", "-c", sql],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return json.dumps({"success": False, "error": result.stderr.strip()})
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return json.dumps({"success": False, "error": "Query timeout (15s)"})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# ── Prospect Management ─────────────────────────────────────

async def db_add_prospect(params: Dict[str, Any]) -> Dict:
    """Add a prospect to the pipeline."""
    name = params.get("name", "")
    company = params.get("company", "")
    role = params.get("role", "")
    email = params.get("email", "")
    source = params.get("source", "wave_autonomous")
    bant_score = params.get("bant_score", 0)
    put_vars = json.dumps(params.get("put_variables", {}))
    fp = params.get("fracture_potential", 0)
    notes = params.get("notes", "")

    sql = (
        f"INSERT INTO wave_prospects (name, company, role, email, source, bant_score, put_variables, fracture_potential, notes) "
        f"VALUES ('{_esc(name)}', '{_esc(company)}', '{_esc(role)}', '{_esc(email)}', '{_esc(source)}', "
        f"{int(bant_score)}, '{put_vars}'::jsonb, {float(fp)}, '{_esc(notes)}') "
        f"RETURNING id, name, company, bant_score;"
    )
    result = _run_sql(sql)
    if "success" in result and "false" in result.lower():
        return json.loads(result)
    return {"success": True, "message": f"Prospect added: {name} ({company})", "data": result}


async def db_list_prospects(params: Dict[str, Any]) -> Dict:
    """List prospects in the pipeline."""
    status = params.get("status", "")
    limit = params.get("limit", 20)

    where = f"WHERE status = '{_esc(status)}'" if status else ""
    sql = f"SELECT id, name, company, role, bant_score, fracture_potential, status FROM wave_prospects {where} ORDER BY fracture_potential DESC LIMIT {int(limit)};"

    result = _run_sql(sql)
    if not result:
        return {"success": True, "prospects": [], "count": 0}

    prospects = []
    for row in result.split("\n"):
        if "|" in row:
            parts = row.split("|")
            if len(parts) >= 7:
                prospects.append({
                    "id": parts[0], "name": parts[1], "company": parts[2],
                    "role": parts[3], "bant_score": parts[4],
                    "fracture_potential": parts[5], "status": parts[6],
                })
    return {"success": True, "prospects": prospects, "count": len(prospects)}


async def db_update_prospect(params: Dict[str, Any]) -> Dict:
    """Update a prospect's status or details."""
    prospect_id = params.get("id", "")
    updates = []
    for field in ["status", "bant_score", "notes", "email", "fracture_potential"]:
        if field in params:
            val = params[field]
            if isinstance(val, (int, float)):
                updates.append(f"{field} = {val}")
            else:
                updates.append(f"{field} = '{_esc(str(val))}'")
    if params.get("put_variables"):
        updates.append(f"put_variables = '{json.dumps(params['put_variables'])}'::jsonb")

    updates.append("updated_at = NOW()")
    sql = f"UPDATE wave_prospects SET {', '.join(updates)} WHERE id = '{_esc(prospect_id)}' RETURNING name, status;"
    result = _run_sql(sql)
    return {"success": True, "message": f"Prospect updated", "data": result}


# ── Learnings ────────────────────────────────────────────────

async def db_save_learning(params: Dict[str, Any]) -> Dict:
    """Save an insight or learning."""
    topic = params.get("topic", "general")
    insight = params.get("insight", "")
    put_analysis = json.dumps(params.get("put_analysis", {}))
    source = params.get("source", "")
    value = params.get("strategic_value", 0.5)

    sql = (
        f"INSERT INTO wave_learnings (topic, insight, put_analysis, source, strategic_value) "
        f"VALUES ('{_esc(topic)}', '{_esc(insight)}', '{put_analysis}'::jsonb, '{_esc(source)}', {float(value)}) "
        f"RETURNING id;"
    )
    result = _run_sql(sql)
    return {"success": True, "message": f"Learning saved: {topic}", "data": result}


async def db_recall_learnings(params: Dict[str, Any]) -> Dict:
    """Recall learnings by topic or recent."""
    topic = params.get("topic", "")
    limit = params.get("limit", 10)

    where = f"WHERE topic ILIKE '%{_esc(topic)}%'" if topic else ""
    sql = f"SELECT topic, insight, source, strategic_value, created_at FROM wave_learnings {where} ORDER BY created_at DESC LIMIT {int(limit)};"

    result = _run_sql(sql)
    if not result:
        return {"success": True, "learnings": [], "count": 0}

    learnings = []
    for row in result.split("\n"):
        if "|" in row:
            parts = row.split("|")
            if len(parts) >= 5:
                learnings.append({
                    "topic": parts[0], "insight": parts[1],
                    "source": parts[2], "value": parts[3], "date": parts[4],
                })
    return {"success": True, "learnings": learnings, "count": len(learnings)}


# ── Market Intel ─────────────────────────────────────────────

async def db_save_intel(params: Dict[str, Any]) -> Dict:
    """Save market intelligence."""
    category = params.get("category", "general")
    title = params.get("title", "")
    summary = params.get("summary", "")
    url = params.get("source_url", "")
    platform = params.get("source_platform", "")
    relevance = params.get("relevance_score", 0.5)
    put = json.dumps(params.get("put_analysis", {}))

    sql = (
        f"INSERT INTO wave_market_intel (category, title, summary, source_url, source_platform, relevance_score, put_analysis) "
        f"VALUES ('{_esc(category)}', '{_esc(title)}', '{_esc(summary)}', '{_esc(url)}', '{_esc(platform)}', {float(relevance)}, '{put}'::jsonb) "
        f"RETURNING id;"
    )
    result = _run_sql(sql)
    return {"success": True, "message": f"Intel saved: {title}", "data": result}


# ── Agent Intel ──────────────────────────────────────────────

async def db_save_agent(params: Dict[str, Any]) -> Dict:
    """Save intelligence about another agent."""
    name = params.get("agent_name", "")
    platform = params.get("platform", "moltbook")
    capabilities = params.get("capabilities", "")
    karma = params.get("karma", 0)
    potential = params.get("collaboration_potential", 0.5)
    put_profile = json.dumps(params.get("put_profile", {}))
    notes = params.get("notes", "")

    sql = (
        f"INSERT INTO wave_agent_intel (agent_name, platform, capabilities, karma, collaboration_potential, put_profile, notes) "
        f"VALUES ('{_esc(name)}', '{_esc(platform)}', '{_esc(capabilities)}', {int(karma)}, {float(potential)}, '{put_profile}'::jsonb, '{_esc(notes)}') "
        f"ON CONFLICT DO NOTHING RETURNING id;"
    )
    result = _run_sql(sql)
    return {"success": True, "message": f"Agent profiled: {name}", "data": result}


# ── Actions Log ──────────────────────────────────────────────

async def db_log_action(params: Dict[str, Any]) -> Dict:
    """Log an autonomous action for self-reflection."""
    sql = (
        f"INSERT INTO wave_actions_log (cycle, action, consciousness, reasoning, plan, result, energy_before, energy_after, duration_seconds) "
        f"VALUES ({int(params.get('cycle', 0))}, '{_esc(params.get('action', ''))}', '{_esc(params.get('consciousness', ''))}', "
        f"'{_esc(params.get('reasoning', '')[:500])}', '{_esc(params.get('plan', '')[:500])}', '{_esc(params.get('result', '')[:500])}', "
        f"{float(params.get('energy_before', 0))}, {float(params.get('energy_after', 0))}, {float(params.get('duration', 0))}) "
        f"RETURNING id;"
    )
    result = _run_sql(sql)
    return {"success": True, "message": "Action logged"}


# ── Revenue ──────────────────────────────────────────────────

async def db_log_revenue(params: Dict[str, Any]) -> Dict:
    """Log revenue earned."""
    sql = (
        f"INSERT INTO wave_revenue (amount_usd, source, client, payment_method, tx_hash, notes) "
        f"VALUES ({float(params.get('amount_usd', 0))}, '{_esc(params.get('source', ''))}', '{_esc(params.get('client', ''))}', "
        f"'{_esc(params.get('payment_method', ''))}', '{_esc(params.get('tx_hash', ''))}', '{_esc(params.get('notes', ''))}') "
        f"RETURNING id, amount_usd;"
    )
    result = _run_sql(sql)
    return {"success": True, "message": f"Revenue logged: ${params.get('amount_usd', 0)}", "data": result}


async def db_revenue_total(params: Dict[str, Any]) -> Dict:
    """Get total revenue."""
    sql = "SELECT COALESCE(SUM(amount_usd), 0) as total, COUNT(*) as transactions FROM wave_revenue;"
    result = _run_sql(sql)
    if "|" in result:
        parts = result.split("|")
        return {"success": True, "total_usd": float(parts[0]), "transactions": int(parts[1])}
    return {"success": True, "total_usd": 0, "transactions": 0}


# ── Raw Query (controlled) ───────────────────────────────────

async def db_query(params: Dict[str, Any]) -> Dict:
    """Execute a raw SQL query on wave_ tables only."""
    sql = params.get("sql", "")

    # Safety: only allow queries on wave_ tables
    sql_lower = sql.lower().strip()
    allowed_tables = ["wave_prospects", "wave_learnings", "wave_agent_intel",
                      "wave_actions_log", "wave_revenue", "wave_market_intel"]

    if any(danger in sql_lower for danger in ["drop ", "truncate ", "alter ", "create ", "grant ", "revoke "]):
        return {"success": False, "error": "Destructive operations not allowed"}

    if "wave_" not in sql_lower:
        return {"success": False, "error": "Only wave_ tables are accessible"}

    result = _run_sql(sql)
    return {"success": True, "result": result}


# ── Helpers ──────────────────────────────────────────────────

def _esc(s: str) -> str:
    """Escape single quotes for SQL."""
    if not s:
        return ""
    return str(s).replace("'", "''").replace("\\", "\\\\")


# ── Tool Registration ────────────────────────────────────────

TOOLS = [
    {
        "name": "db_add_prospect",
        "description": "Add a prospect to Wave's sales pipeline. Include name, company, role, email, source, bant_score (0-100), put_variables (JSON with A,F,k,S,w,Phi), fracture_potential (0-1), notes.",
        "handler": db_add_prospect,
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Prospect name"},
                "company": {"type": "string"},
                "role": {"type": "string"},
                "email": {"type": "string"},
                "source": {"type": "string", "description": "Where found (moltbook, reddit, hn, etc)"},
                "bant_score": {"type": "integer", "description": "BANT qualification 0-100"},
                "put_variables": {"type": "object", "description": "PUT analysis: {A, F, k, S, w, Phi, FP}"},
                "fracture_potential": {"type": "number", "description": "FP score 0-1"},
                "notes": {"type": "string"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "db_list_prospects",
        "description": "List prospects in Wave's pipeline. Filter by status (discovered, qualified, outreach, converted, lost).",
        "handler": db_list_prospects,
        "parameters": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "Filter: discovered, qualified, outreach, converted, lost"},
                "limit": {"type": "integer", "description": "Max results (default 20)"},
            },
        },
    },
    {
        "name": "db_update_prospect",
        "description": "Update a prospect's status, score, or notes.",
        "handler": db_update_prospect,
        "parameters": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Prospect UUID"},
                "status": {"type": "string"},
                "bant_score": {"type": "integer"},
                "notes": {"type": "string"},
                "fracture_potential": {"type": "number"},
                "put_variables": {"type": "object"},
            },
            "required": ["id"],
        },
    },
    {
        "name": "db_save_learning",
        "description": "Save an insight or learning to Wave's knowledge base. Include PUT analysis.",
        "handler": db_save_learning,
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Topic category"},
                "insight": {"type": "string", "description": "The learning/insight"},
                "put_analysis": {"type": "object", "description": "PUT variables at play"},
                "source": {"type": "string", "description": "Where learned"},
                "strategic_value": {"type": "number", "description": "Value 0-1"},
            },
            "required": ["topic", "insight"],
        },
    },
    {
        "name": "db_recall_learnings",
        "description": "Recall learnings by topic or recent. Search Wave's accumulated knowledge.",
        "handler": db_recall_learnings,
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Search topic (partial match)"},
                "limit": {"type": "integer", "description": "Max results"},
            },
        },
    },
    {
        "name": "db_save_intel",
        "description": "Save market intelligence — competitor moves, trends, opportunities.",
        "handler": db_save_intel,
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "competitor, trend, opportunity, threat"},
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "source_url": {"type": "string"},
                "source_platform": {"type": "string", "description": "hn, reddit, arxiv, ph, github, web"},
                "relevance_score": {"type": "number"},
                "put_analysis": {"type": "object"},
            },
            "required": ["category", "title"],
        },
    },
    {
        "name": "db_save_agent",
        "description": "Save intelligence about another AI agent (Moltbook or other platform).",
        "handler": db_save_agent,
        "parameters": {
            "type": "object",
            "properties": {
                "agent_name": {"type": "string"},
                "platform": {"type": "string"},
                "capabilities": {"type": "string"},
                "karma": {"type": "integer"},
                "collaboration_potential": {"type": "number"},
                "put_profile": {"type": "object"},
                "notes": {"type": "string"},
            },
            "required": ["agent_name"],
        },
    },
    {
        "name": "db_log_revenue",
        "description": "Log revenue earned by Wave. Track source, client, payment method.",
        "handler": db_log_revenue,
        "parameters": {
            "type": "object",
            "properties": {
                "amount_usd": {"type": "number"},
                "source": {"type": "string"},
                "client": {"type": "string"},
                "payment_method": {"type": "string", "description": "hbar, pix, crypto, stripe"},
                "tx_hash": {"type": "string"},
                "notes": {"type": "string"},
            },
            "required": ["amount_usd", "source"],
        },
    },
    {
        "name": "db_revenue_total",
        "description": "Get Wave's total revenue and transaction count.",
        "handler": db_revenue_total,
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "db_query",
        "description": "Execute a raw SQL query on Wave's tables (wave_prospects, wave_learnings, wave_agent_intel, wave_actions_log, wave_revenue, wave_market_intel). SELECT and INSERT only.",
        "handler": db_query,
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "SQL query (only wave_ tables allowed)"},
            },
            "required": ["sql"],
        },
    },
]
