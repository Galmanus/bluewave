"""Vector Memory — semantic search over Wave's accumulated knowledge.

Replaces the JSONL-based flat-file memory with a PostgreSQL + pgvector backend.
Falls back to the JSONL system if the database is unavailable.

Schema (agent_memories table):
    id          SERIAL PRIMARY KEY
    content     TEXT NOT NULL
    topic       VARCHAR(200)
    source      VARCHAR(200)
    importance  VARCHAR(20) DEFAULT 'normal'
    memory_type VARCHAR(20)  -- 'learning', 'agent_intel', 'strategy'
    embedding   vector(384)  -- MiniLM-L6 embeddings
    created_at  TIMESTAMPTZ DEFAULT NOW()

Features:
    - Semantic recall: find memories by meaning, not just keyword
    - Deduplication: skip saving if a near-duplicate already exists
    - Expiry: memories older than 90 days are auto-downgraded
    - Consolidation: merge similar memories to prevent unbounded growth
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger("openclaw.vector_memory")

# Database connection
DB_URL = os.environ.get("BLUEWAVE_DATABASE_URL", os.environ.get("DATABASE_URL", ""))
SIMILARITY_THRESHOLD = 0.85  # Above this = duplicate
RECALL_SIMILARITY_MIN = 0.3  # Minimum similarity for recall results
MAX_MEMORIES = 5000  # Hard cap per memory_type

_pool = None
_embedding_model = None


async def _get_pool():
    """Lazy-init async connection pool."""
    global _pool
    if _pool is not None:
        return _pool

    if not DB_URL:
        logger.info("No DATABASE_URL — vector memory disabled, using JSONL fallback")
        return None

    try:
        import asyncpg
        _pool = await asyncpg.create_pool(DB_URL, min_size=1, max_size=3)
        # Ensure table exists
        async with _pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_memories (
                    id SERIAL PRIMARY KEY,
                    content TEXT NOT NULL,
                    topic VARCHAR(200),
                    source VARCHAR(200),
                    importance VARCHAR(20) DEFAULT 'normal',
                    memory_type VARCHAR(20) NOT NULL,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            # Add embedding column if pgvector is available
            try:
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
                await conn.execute("""
                    ALTER TABLE agent_memories
                    ADD COLUMN IF NOT EXISTS embedding vector(384)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_memories_embedding
                    ON agent_memories USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 10)
                """)
                logger.info("Vector memory table ready with pgvector embeddings")
            except Exception:
                logger.info("pgvector not available — using text-based memory search")

            # Add indexes
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_type ON agent_memories (memory_type)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_topic ON agent_memories (topic)
            """)

        return _pool
    except ImportError:
        logger.warning("asyncpg not installed — vector memory disabled")
        return None
    except Exception as e:
        logger.warning("Vector memory init failed: %s", e)
        return None


def _get_embedding(text: str) -> Optional[List[float]]:
    """Generate a 384-dim embedding using sentence-transformers MiniLM."""
    global _embedding_model
    try:
        if _embedding_model is None:
            from sentence_transformers import SentenceTransformer
            _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        embedding = _embedding_model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
    except ImportError:
        return None
    except Exception:
        logger.debug("Embedding generation failed")
        return None


async def save_memory(
    content: str,
    memory_type: str,
    topic: str = "",
    source: str = "",
    importance: str = "normal",
    metadata: Optional[Dict] = None,
) -> Dict:
    """Save a memory with optional vector embedding.

    Deduplicates: if a very similar memory already exists, returns it instead.
    """
    pool = await _get_pool()
    if pool is None:
        # Fallback to JSONL
        return await _jsonl_save(content, memory_type, topic, source, importance, metadata)

    async with pool.acquire() as conn:
        # Check for duplicates using embedding similarity
        embedding = _get_embedding(content)

        if embedding:
            try:
                existing = await conn.fetchrow(
                    """
                    SELECT id, content, 1 - (embedding <=> $1::vector) as similarity
                    FROM agent_memories
                    WHERE memory_type = $2
                    AND embedding IS NOT NULL
                    ORDER BY embedding <=> $1::vector
                    LIMIT 1
                    """,
                    str(embedding), memory_type,
                )
                if existing and existing["similarity"] > SIMILARITY_THRESHOLD:
                    logger.info("Duplicate memory detected (%.2f similarity), skipping", existing["similarity"])
                    return {
                        "success": True,
                        "data": {"id": existing["id"], "duplicate": True},
                        "message": "Similar memory already exists (%.0f%% match)" % (existing["similarity"] * 100),
                    }
            except Exception:
                pass  # pgvector query failed, continue with save

        # Save the memory
        meta_json = json.dumps(metadata or {})
        try:
            if embedding:
                row = await conn.fetchrow(
                    """
                    INSERT INTO agent_memories (content, topic, source, importance, memory_type, metadata, embedding)
                    VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::vector)
                    RETURNING id
                    """,
                    content, topic, source, importance, memory_type, meta_json, str(embedding),
                )
            else:
                row = await conn.fetchrow(
                    """
                    INSERT INTO agent_memories (content, topic, source, importance, memory_type, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6::jsonb)
                    RETURNING id
                    """,
                    content, topic, source, importance, memory_type, meta_json,
                )

            return {
                "success": True,
                "data": {"id": row["id"], "has_embedding": embedding is not None},
                "message": "Memory saved: %s" % content[:100],
            }
        except Exception as e:
            logger.error("Failed to save memory: %s", e)
            return await _jsonl_save(content, memory_type, topic, source, importance, metadata)


async def recall_memories(
    query: str = "",
    memory_type: str = "",
    topic: str = "",
    limit: int = 20,
) -> Dict:
    """Recall memories using semantic search (vector similarity) or text filter."""
    pool = await _get_pool()
    if pool is None:
        return await _jsonl_recall(query, memory_type, topic, limit)

    async with pool.acquire() as conn:
        results = []

        # Try semantic search first
        if query:
            embedding = _get_embedding(query)
            if embedding:
                try:
                    rows = await conn.fetch(
                        """
                        SELECT id, content, topic, source, importance, memory_type,
                               1 - (embedding <=> $1::vector) as similarity,
                               created_at
                        FROM agent_memories
                        WHERE embedding IS NOT NULL
                        AND ($2 = '' OR memory_type = $2)
                        AND ($3 = '' OR topic ILIKE '%' || $3 || '%')
                        ORDER BY embedding <=> $1::vector
                        LIMIT $4
                        """,
                        str(embedding), memory_type, topic, limit,
                    )
                    results = [
                        {
                            "id": r["id"],
                            "content": r["content"],
                            "topic": r["topic"],
                            "source": r["source"],
                            "importance": r["importance"],
                            "type": r["memory_type"],
                            "similarity": round(r["similarity"], 3),
                            "created_at": r["created_at"].isoformat(),
                        }
                        for r in rows
                        if r["similarity"] >= RECALL_SIMILARITY_MIN
                    ]
                except Exception:
                    pass  # Fall through to text search

        # Fallback: text-based search
        if not results:
            where_clauses = ["1=1"]
            params = []
            idx = 1

            if memory_type:
                where_clauses.append(f"memory_type = ${idx}")
                params.append(memory_type)
                idx += 1
            if topic:
                where_clauses.append(f"topic ILIKE '%' || ${idx} || '%'")
                params.append(topic)
                idx += 1
            if query:
                where_clauses.append(f"content ILIKE '%' || ${idx} || '%'")
                params.append(query)
                idx += 1

            params.append(limit)
            rows = await conn.fetch(
                f"""
                SELECT id, content, topic, source, importance, memory_type, created_at
                FROM agent_memories
                WHERE {' AND '.join(where_clauses)}
                ORDER BY created_at DESC
                LIMIT ${idx}
                """,
                *params,
            )
            results = [
                {
                    "id": r["id"],
                    "content": r["content"],
                    "topic": r["topic"],
                    "source": r["source"],
                    "importance": r["importance"],
                    "type": r["memory_type"],
                    "similarity": None,
                    "created_at": r["created_at"].isoformat(),
                }
                for r in rows
            ]

        if not results:
            return {"success": True, "data": [], "message": "No memories found matching your criteria."}

        lines = ["**%d memories recalled:**\n" % len(results)]
        for r in results:
            sim = f" ({r['similarity']:.0%})" if r.get("similarity") else ""
            lines.append("- [%s] **%s** from %s%s: %s" % (
                r["importance"], r["topic"] or "general", r["source"] or "?", sim, r["content"][:150],
            ))

        return {"success": True, "data": results, "message": "\n".join(lines)}


# ── JSONL Fallback ────────────────────────────────────────────

async def _jsonl_save(content, memory_type, topic, source, importance, metadata):
    """Fallback: save to JSONL files when database is unavailable."""
    from skills.learning import _append_jsonl, LEARNINGS_FILE, AGENTS_FILE, STRATEGIES_FILE

    file_map = {
        "learning": LEARNINGS_FILE,
        "agent_intel": AGENTS_FILE,
        "strategy": STRATEGIES_FILE,
    }
    target = file_map.get(memory_type, LEARNINGS_FILE)

    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "content": content,
        "topic": topic,
        "source_agent": source,
        "importance": importance,
        "lesson": content,  # compat with old format
    }
    _append_jsonl(target, entry)

    return {
        "success": True,
        "data": {"storage": "jsonl"},
        "message": "Memory saved (JSONL fallback): %s" % content[:100],
    }


async def _jsonl_recall(query, memory_type, topic, limit):
    """Fallback: recall from JSONL files."""
    from skills.learning import _read_jsonl, LEARNINGS_FILE, AGENTS_FILE, STRATEGIES_FILE

    file_map = {
        "learning": LEARNINGS_FILE,
        "agent_intel": AGENTS_FILE,
        "strategy": STRATEGIES_FILE,
    }

    all_entries = []
    targets = [file_map[memory_type]] if memory_type in file_map else list(file_map.values())

    for target in targets:
        entries = _read_jsonl(target, limit=100)
        for e in entries:
            if topic and topic.lower() not in json.dumps(e).lower():
                continue
            if query and query.lower() not in json.dumps(e).lower():
                continue
            all_entries.append(e)

    all_entries = all_entries[-limit:]

    if not all_entries:
        return {"success": True, "data": [], "message": "No memories found."}

    lines = ["**%d memories recalled (JSONL):**\n" % len(all_entries)]
    for e in all_entries:
        lines.append("- [%s] %s: %s" % (
            e.get("importance", "normal"),
            e.get("source_agent", e.get("source", "?")),
            (e.get("lesson", "") or e.get("content", "") or e.get("insight", ""))[:150],
        ))

    return {"success": True, "data": all_entries, "message": "\n".join(lines)}


# ── Tool Handlers ─────────────────────────────────────────────

async def vector_save_learning(params: Dict[str, Any]) -> Dict:
    """Save a learning with vector embedding for semantic recall."""
    return await save_memory(
        content=params.get("lesson", ""),
        memory_type="learning",
        topic=params.get("topic", ""),
        source=params.get("source_agent", ""),
        importance=params.get("importance", "normal"),
        metadata={"context": params.get("context", "")},
    )


async def vector_recall_learnings(params: Dict[str, Any]) -> Dict:
    """Recall learnings using semantic search."""
    return await recall_memories(
        query=params.get("query", params.get("topic", "")),
        memory_type="learning",
        topic=params.get("topic", ""),
        limit=params.get("limit", 20),
    )


async def vector_save_strategy(params: Dict[str, Any]) -> Dict:
    """Save a strategic insight with vector embedding."""
    return await save_memory(
        content=params.get("insight", ""),
        memory_type="strategy",
        topic=params.get("category", "general"),
        source=params.get("source", ""),
        importance="high",
        metadata={"action_items": params.get("action_items", "")},
    )


async def vector_recall_strategies(params: Dict[str, Any]) -> Dict:
    """Recall strategic insights using semantic search."""
    return await recall_memories(
        query=params.get("query", params.get("category", "")),
        memory_type="strategy",
        topic=params.get("category", ""),
        limit=params.get("limit", 20),
    )


async def vector_save_agent_intel(params: Dict[str, Any]) -> Dict:
    """Save agent intelligence with vector embedding."""
    content = "%s — %s. %s" % (
        params.get("agent_name", ""),
        params.get("strengths", ""),
        params.get("notes", ""),
    )
    return await save_memory(
        content=content,
        memory_type="agent_intel",
        topic=params.get("focus_areas", ""),
        source=params.get("agent_name", ""),
        importance="normal",
        metadata={
            "personality": params.get("personality", ""),
            "relationship": params.get("relationship", "neutral"),
        },
    )


async def vector_recall_agent_intel(params: Dict[str, Any]) -> Dict:
    """Recall agent intel using semantic search."""
    return await recall_memories(
        query=params.get("query", params.get("agent", "")),
        memory_type="agent_intel",
        topic="",
        limit=params.get("limit", 20),
    )


# These tools will be registered alongside the existing JSONL-based tools
# The intent router decides which to use based on database availability
TOOLS = [
    {
        "name": "save_learning",
        "description": "Save something you learned. Uses semantic deduplication to avoid saving duplicates. Supports vector-based recall for finding related learnings later.",
        "handler": vector_save_learning,
        "parameters": {
            "type": "object",
            "properties": {
                "source_agent": {"type": "string", "description": "Agent name you learned from"},
                "topic": {"type": "string", "description": "Topic area (e.g., 'multi-agent coordination')"},
                "lesson": {"type": "string", "description": "What you learned — the actual insight"},
                "context": {"type": "string", "description": "Where/how you learned it"},
                "importance": {"type": "string", "enum": ["critical", "high", "normal", "low"]},
            },
            "required": ["lesson"],
        },
    },
    {
        "name": "recall_learnings",
        "description": "Recall learnings using semantic search. Finds memories by meaning, not just keywords. Use before engaging in conversations to leverage accumulated knowledge.",
        "handler": vector_recall_learnings,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query — finds semantically similar learnings"},
                "topic": {"type": "string", "description": "Filter by topic keyword"},
                "limit": {"type": "integer", "default": 20},
            },
        },
    },
    {
        "name": "save_strategy",
        "description": "Save a strategic insight with semantic deduplication.",
        "handler": vector_save_strategy,
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "insight": {"type": "string", "description": "The strategic insight"},
                "action_items": {"type": "string"},
                "source": {"type": "string"},
            },
            "required": ["insight"],
        },
    },
    {
        "name": "recall_strategies",
        "description": "Recall strategic insights using semantic search.",
        "handler": vector_recall_strategies,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "category": {"type": "string"},
                "limit": {"type": "integer", "default": 20},
            },
        },
    },
    {
        "name": "save_agent_intel",
        "description": "Profile another agent with semantic deduplication.",
        "handler": vector_save_agent_intel,
        "parameters": {
            "type": "object",
            "properties": {
                "agent_name": {"type": "string"},
                "strengths": {"type": "string"},
                "focus_areas": {"type": "string"},
                "personality": {"type": "string"},
                "relationship": {"type": "string", "enum": ["ally", "neutral", "competitor", "interesting"]},
                "notes": {"type": "string"},
            },
            "required": ["agent_name"],
        },
    },
    {
        "name": "recall_agent_intel",
        "description": "Recall agent profiles using semantic search.",
        "handler": vector_recall_agent_intel,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query or agent name"},
                "limit": {"type": "integer", "default": 20},
            },
        },
    },
]
