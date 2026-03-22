"""
Swarm Simulation Engine — MiroFish-inspired multi-agent simulation for Wave.

Creates populations of agents with distinct personalities, simulates their
interactions on a virtual social platform, and produces predictive reports.

Native to Wave's stack: Python 3.8+, Anthropic API, no external dependencies.
Inspired by MiroFish (666ghj) but rebuilt from scratch for the ASA ecosystem.

Created by Manuel Guilherme Galmanus, 2026.

Usage:
    from skills.swarm_simulation import TOOLS
    # create_simulation -> run_simulation -> get_simulation_report
"""

import asyncio
import json
import logging
import os
import time
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("openclaw.swarm")

SIMULATIONS_DIR = Path(__file__).parent.parent / "memory" / "simulations"
SIMULATIONS_DIR.mkdir(parents=True, exist_ok=True)


# ── Data Models ───────────────────────────────────────────────

@dataclass
class SimAgent:
    """A simulated agent with personality and behavior."""
    id: int
    name: str
    role: str
    personality: str
    stance: str  # supportive, opposing, neutral, observer
    influence: float  # 0.0 - 1.0
    activity: float  # 0.0 - 1.0 (chance to act per round)
    # PUT variables for behavioral depth
    A: float = 0.5  # ambition
    F: float = 0.5  # fear
    k: float = 0.2  # shadow coefficient
    S: float = 0.5  # status
    w: float = 0.3  # pain
    posts: List[Dict] = field(default_factory=list)
    interactions: List[Dict] = field(default_factory=list)

    def to_dict(self):
        d = asdict(self)
        d["posts"] = d["posts"][-5:]  # Keep last 5 for context
        d["interactions"] = d["interactions"][-5:]
        return d


@dataclass
class SimPost:
    """A post in the simulation."""
    id: int
    author_id: int
    author_name: str
    content: str
    round_num: int
    timestamp: str
    likes: int = 0
    comments: List[Dict] = field(default_factory=list)
    sentiment: float = 0.0  # -1.0 to 1.0


@dataclass
class SimState:
    """Full simulation state."""
    sim_id: str
    scenario: str
    num_agents: int
    num_rounds: int
    current_round: int = 0
    status: str = "created"  # created, running, completed, failed
    agents: List[SimAgent] = field(default_factory=list)
    posts: List[SimPost] = field(default_factory=list)
    events: List[Dict] = field(default_factory=list)
    round_summaries: List[Dict] = field(default_factory=list)
    report: str = ""
    created_at: str = ""
    completed_at: str = ""


# ── Core Engine ───────────────────────────────────────────────

async def _llm_call(prompt: str, system: str = "", max_tokens: int = 1500) -> str:
    """Call Claude via CLI engine (free on Max plan) or API fallback."""
    # Primary: Claude CLI Engine (free, unlimited on Max plan)
    try:
        sys_path = str(Path(__file__).parent.parent)
        if sys_path not in __import__('sys').path:
            __import__('sys').path.insert(0, sys_path)
        from claude_engine import claude_call
        full_prompt = prompt
        if system:
            full_prompt = f"{system}\n\n{prompt}"
        result = await claude_call(
            prompt=full_prompt,
            model="haiku",
            timeout=60,
            max_turns=1,
        )
        if result.get("success"):
            return result["response"]
    except Exception as e:
        logger.debug("Claude Engine unavailable: %s", e)

    # Fallback: Anthropic API
    try:
        import anthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return ""
        client = anthropic.AsyncAnthropic(api_key=api_key)
        msgs = [{"role": "user", "content": prompt}]
        kwargs = {"model": "claude-haiku-4-5-20251001", "max_tokens": max_tokens, "messages": msgs}
        if system:
            kwargs["system"] = system
        resp = await client.messages.create(**kwargs)
        return resp.content[0].text
    except Exception as e:
        logger.debug("API fallback failed: %s", e)
        return ""


async def _generate_agents(scenario: str, num_agents: int) -> List[SimAgent]:
    """Generate a diverse population of agents for the scenario."""
    prompt = f"""Generate {num_agents} diverse simulated agents for this scenario:

SCENARIO: {scenario}

For each agent, provide a JSON array with objects containing:
- name: realistic name
- role: their role/position (CEO, engineer, journalist, citizen, investor, etc)
- personality: 2-3 sentences describing personality, values, communication style
- stance: one of "supportive", "opposing", "neutral", "observer"
- influence: 0.0-1.0 (how much others listen to them)
- activity: 0.0-1.0 (how often they post/comment)
- A: 0.0-1.0 (ambition level)
- F: 0.0-1.0 (fear/caution level)
- S: 0.0-1.0 (status/authority level)

Requirements:
- Mix of stances: ~30% supportive, ~25% opposing, ~25% neutral, ~20% observer
- Mix of influence: 2-3 high (>0.7), most medium (0.3-0.7), some low (<0.3)
- Diverse roles, ages, perspectives
- Realistic personalities that will produce interesting debates

Return ONLY a JSON array, no other text."""

    raw = await _llm_call(prompt, max_tokens=3000)

    # Parse JSON from response
    try:
        # Find JSON array in response
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            agents_data = json.loads(raw[start:end])
        else:
            agents_data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Failed to parse agents JSON, generating defaults")
        agents_data = [
            {"name": f"Agent_{i}", "role": "participant", "personality": "Average citizen",
             "stance": random.choice(["supportive", "opposing", "neutral", "observer"]),
             "influence": random.uniform(0.2, 0.8), "activity": random.uniform(0.3, 0.8),
             "A": random.uniform(0.3, 0.8), "F": random.uniform(0.2, 0.7), "S": random.uniform(0.2, 0.8)}
            for i in range(num_agents)
        ]

    agents = []
    for i, data in enumerate(agents_data[:num_agents]):
        agents.append(SimAgent(
            id=i,
            name=data.get("name", f"Agent_{i}"),
            role=data.get("role", "participant"),
            personality=data.get("personality", "Average person with moderate views"),
            stance=data.get("stance", "neutral"),
            influence=float(data.get("influence", 0.5)),
            activity=float(data.get("activity", 0.5)),
            A=float(data.get("A", 0.5)),
            F=float(data.get("F", 0.5)),
            k=random.uniform(0.1, 0.5),
            S=float(data.get("S", 0.5)),
            w=random.uniform(0.1, 0.5),
        ))

    return agents


async def _simulate_round(state: SimState, round_num: int) -> Dict:
    """Simulate one round of interactions."""
    active_agents = [a for a in state.agents if random.random() < a.activity]
    if not active_agents:
        active_agents = random.sample(state.agents, min(3, len(state.agents)))

    round_posts = []
    round_comments = []

    # Recent context for agents
    recent_posts = state.posts[-10:] if state.posts else []
    recent_context = "\n".join([
        f"- {p.author_name}: \"{p.content[:100]}\" ({p.likes} likes)"
        for p in recent_posts
    ]) if recent_posts else "No posts yet."

    # Events for this round
    round_events = [e for e in state.events if e.get("round") == round_num]
    event_text = "\n".join([f"EVENT: {e['description']}" for e in round_events]) if round_events else ""

    # Each active agent decides what to do
    for agent in active_agents[:8]:  # Max 8 agents per round to control costs
        action_prompt = f"""You are simulating {agent.name} ({agent.role}).

PERSONALITY: {agent.personality}
STANCE on the topic: {agent.stance}
INFLUENCE: {agent.influence:.1f}/1.0 | AMBITION: {agent.A:.1f} | FEAR: {agent.F:.1f} | STATUS: {agent.S:.1f}

SCENARIO: {state.scenario}
ROUND: {round_num}/{state.num_rounds}

RECENT ACTIVITY:
{recent_context}

{event_text}

As {agent.name}, choose ONE action:
1. POST: Write an original post (2-4 sentences) expressing your view
2. COMMENT: Reply to a recent post (1-2 sentences)
3. NOTHING: Stay silent this round

Respond in this exact format:
ACTION: POST|COMMENT|NOTHING
TARGET: (post author name if commenting, empty if posting)
CONTENT: (your post/comment text, empty if nothing)
SENTIMENT: (number -1.0 to 1.0, negative=critical, positive=supportive)"""

        raw = await _llm_call(action_prompt, max_tokens=300)

        # Parse action
        action = "NOTHING"
        content = ""
        sentiment = 0.0
        target = ""

        for line in raw.split("\n"):
            line = line.strip()
            if line.startswith("ACTION:"):
                action = line.split(":", 1)[1].strip().upper()
            elif line.startswith("CONTENT:"):
                content = line.split(":", 1)[1].strip()
            elif line.startswith("SENTIMENT:"):
                try:
                    sentiment = float(line.split(":", 1)[1].strip())
                except ValueError:
                    sentiment = 0.0
            elif line.startswith("TARGET:"):
                target = line.split(":", 1)[1].strip()

        if action == "POST" and content:
            post = SimPost(
                id=len(state.posts) + len(round_posts),
                author_id=agent.id,
                author_name=agent.name,
                content=content,
                round_num=round_num,
                timestamp=datetime.utcnow().isoformat(),
                sentiment=sentiment,
            )
            round_posts.append(post)
            agent.posts.append({"round": round_num, "content": content[:100]})

        elif action == "COMMENT" and content and recent_posts:
            # Find target post
            target_post = None
            if target:
                for p in reversed(state.posts):
                    if target.lower() in p.author_name.lower():
                        target_post = p
                        break
            if not target_post and state.posts:
                target_post = random.choice(state.posts[-5:])

            if target_post:
                comment = {
                    "author_id": agent.id,
                    "author_name": agent.name,
                    "content": content,
                    "sentiment": sentiment,
                    "round": round_num,
                }
                target_post.comments.append(comment)
                round_comments.append(comment)
                agent.interactions.append({
                    "round": round_num,
                    "type": "comment",
                    "target": target_post.author_name,
                    "content": content[:80],
                })

        # Simulate likes based on influence
        for post in round_posts:
            for other in state.agents:
                if other.id != post.author_id and random.random() < 0.3:
                    # Like probability based on stance alignment
                    if other.stance == "supportive" and post.sentiment > 0:
                        post.likes += 1
                    elif other.stance == "opposing" and post.sentiment < 0:
                        post.likes += 1
                    elif other.stance == "neutral" and random.random() < 0.3:
                        post.likes += 1

    state.posts.extend(round_posts)

    # Round summary
    summary = {
        "round": round_num,
        "active_agents": len(active_agents),
        "new_posts": len(round_posts),
        "new_comments": len(round_comments),
        "avg_sentiment": sum(p.sentiment for p in round_posts) / max(len(round_posts), 1),
        "top_post": round_posts[0].content[:80] if round_posts else "no posts",
        "events": [e["description"] for e in round_events],
    }
    state.round_summaries.append(summary)

    return summary


async def _generate_report(state: SimState) -> str:
    """Generate a predictive report from simulation results."""
    # Compile simulation data
    total_posts = len(state.posts)
    total_comments = sum(len(p.comments) for p in state.posts)
    avg_sentiment = sum(p.sentiment for p in state.posts) / max(total_posts, 1)

    # Top posts by engagement
    top_posts = sorted(state.posts, key=lambda p: p.likes + len(p.comments), reverse=True)[:5]
    top_posts_text = "\n".join([
        f"- {p.author_name} ({p.likes} likes, {len(p.comments)} comments): \"{p.content[:120]}\""
        for p in top_posts
    ])

    # Stance distribution
    stances = {}
    for a in state.agents:
        stances[a.stance] = stances.get(a.stance, 0) + 1

    # Sentiment evolution
    sentiment_by_round = []
    for s in state.round_summaries:
        sentiment_by_round.append(f"Round {s['round']}: {s['avg_sentiment']:.2f} ({s['new_posts']} posts)")

    # Agent activity ranking
    agent_activity = sorted(state.agents, key=lambda a: len(a.posts) + len(a.interactions), reverse=True)[:5]
    active_text = "\n".join([
        f"- {a.name} ({a.role}): {len(a.posts)} posts, {len(a.interactions)} interactions, stance={a.stance}"
        for a in agent_activity
    ])

    report_prompt = f"""Analyze this multi-agent simulation and produce a strategic prediction report.

SCENARIO: {state.scenario}

SIMULATION STATS:
- {state.num_agents} agents simulated over {state.num_rounds} rounds
- {total_posts} total posts, {total_comments} total comments
- Average sentiment: {avg_sentiment:.2f} (-1=negative, +1=positive)
- Stance distribution: {json.dumps(stances)}

SENTIMENT EVOLUTION:
{chr(10).join(sentiment_by_round)}

TOP POSTS (by engagement):
{top_posts_text}

MOST ACTIVE AGENTS:
{active_text}

EVENTS INJECTED:
{chr(10).join([f"Round {e.get('round', '?')}: {e.get('description', '')}" for e in state.events]) if state.events else "None"}

Write a prediction report with these sections:
1. EXECUTIVE SUMMARY (3-4 sentences)
2. KEY FINDINGS (5 bullet points)
3. SENTIMENT ANALYSIS (trend, turning points, drivers)
4. STAKEHOLDER MAP (who matters, who doesn't, alliances)
5. PREDICTION (what will happen next, with confidence %)
6. STRATEGIC RECOMMENDATIONS (3 actionable items)
7. PUT ANALYSIS (apply Psychometric Utility Theory variables to key actors)

Be specific, use data from the simulation, and provide actionable intelligence."""

    report = await _llm_call(report_prompt, max_tokens=3000)
    return report


# ── Tool Handlers ─────────────────────────────────────────────

async def create_simulation(params: Dict[str, Any]) -> Dict:
    """Create a new swarm simulation with generated agents."""
    scenario = params.get("scenario", "")
    num_agents = min(int(params.get("num_agents", 10)), 30)  # Cap at 30
    num_rounds = min(int(params.get("num_rounds", 5)), 15)  # Cap at 15
    events = params.get("events", [])  # [{round: N, description: "..."}]

    if not scenario:
        return {"success": False, "data": None, "message": "Need a scenario description"}

    sim_id = f"sim_{int(time.time())}_{random.randint(1000, 9999)}"

    logger.info("Creating simulation: %s agents, %s rounds", num_agents, num_rounds)

    # Generate agents
    agents = await _generate_agents(scenario, num_agents)

    state = SimState(
        sim_id=sim_id,
        scenario=scenario,
        num_agents=len(agents),
        num_rounds=num_rounds,
        agents=agents,
        events=events,
        created_at=datetime.utcnow().isoformat(),
    )

    # Save state
    sim_file = SIMULATIONS_DIR / f"{sim_id}.json"
    _save_state(state, sim_file)

    return {
        "success": True,
        "data": {
            "sim_id": sim_id,
            "scenario": scenario,
            "agents": [{"name": a.name, "role": a.role, "stance": a.stance,
                        "influence": a.influence, "A": a.A, "F": a.F, "S": a.S}
                       for a in agents],
            "num_rounds": num_rounds,
            "events": events,
        },
        "message": f"Simulation created with {len(agents)} agents. Use run_simulation to start."
    }


async def run_simulation(params: Dict[str, Any]) -> Dict:
    """Run a simulation round by round."""
    sim_id = params.get("sim_id", "")

    sim_file = SIMULATIONS_DIR / f"{sim_id}.json"
    if not sim_file.exists():
        return {"success": False, "data": None, "message": f"Simulation {sim_id} not found"}

    state = _load_state(sim_file)
    state.status = "running"

    results = []
    for round_num in range(1, state.num_rounds + 1):
        state.current_round = round_num
        logger.info("Simulation %s: round %d/%d", sim_id, round_num, state.num_rounds)

        summary = await _simulate_round(state, round_num)
        results.append(summary)

        # Save after each round
        _save_state(state, sim_file)

        # Small delay to avoid API rate limits
        await asyncio.sleep(0.5)

    # Generate report
    state.report = await _generate_report(state)
    state.status = "completed"
    state.completed_at = datetime.utcnow().isoformat()
    _save_state(state, sim_file)

    return {
        "success": True,
        "data": {
            "sim_id": sim_id,
            "rounds_completed": state.num_rounds,
            "total_posts": len(state.posts),
            "total_comments": sum(len(p.comments) for p in state.posts),
            "round_summaries": results,
        },
        "message": f"Simulation completed. {len(state.posts)} posts generated across {state.num_rounds} rounds."
    }


async def get_simulation_report(params: Dict[str, Any]) -> Dict:
    """Get the prediction report from a completed simulation."""
    sim_id = params.get("sim_id", "")

    sim_file = SIMULATIONS_DIR / f"{sim_id}.json"
    if not sim_file.exists():
        return {"success": False, "data": None, "message": f"Simulation {sim_id} not found"}

    state = _load_state(sim_file)

    if not state.report:
        return {"success": False, "data": None, "message": "Simulation not completed yet. Run it first."}

    # Compile stats
    stance_counts = {}
    for a in state.agents:
        stance_counts[a.stance] = stance_counts.get(a.stance, 0) + 1

    return {
        "success": True,
        "data": {
            "sim_id": sim_id,
            "scenario": state.scenario,
            "report": state.report,
            "stats": {
                "agents": state.num_agents,
                "rounds": state.num_rounds,
                "posts": len(state.posts),
                "comments": sum(len(p.comments) for p in state.posts),
                "stances": stance_counts,
                "avg_sentiment": sum(p.sentiment for p in state.posts) / max(len(state.posts), 1),
            },
        },
        "message": "Report generated successfully."
    }


async def quick_predict(params: Dict[str, Any]) -> Dict:
    """Quick prediction: create, run, and report in one call."""
    scenario = params.get("scenario", "")
    num_agents = min(int(params.get("num_agents", 8)), 20)
    num_rounds = min(int(params.get("num_rounds", 3)), 8)
    events = params.get("events", [])

    if not scenario:
        return {"success": False, "data": None, "message": "Need a scenario description"}

    # Create
    create_result = await create_simulation({
        "scenario": scenario,
        "num_agents": num_agents,
        "num_rounds": num_rounds,
        "events": events,
    })

    if not create_result["success"]:
        return create_result

    sim_id = create_result["data"]["sim_id"]

    # Run
    run_result = await run_simulation({"sim_id": sim_id})

    if not run_result["success"]:
        return run_result

    # Report
    report_result = await get_simulation_report({"sim_id": sim_id})

    return report_result


async def list_simulations(params: Dict[str, Any]) -> Dict:
    """List all simulations."""
    sims = []
    for f in sorted(SIMULATIONS_DIR.glob("sim_*.json"), reverse=True):
        try:
            state = _load_state(f)
            sims.append({
                "sim_id": state.sim_id,
                "scenario": state.scenario[:80],
                "status": state.status,
                "agents": state.num_agents,
                "rounds": state.num_rounds,
                "posts": len(state.posts),
                "created": state.created_at,
            })
        except Exception:
            continue

    return {
        "success": True,
        "data": {"simulations": sims[:20]},
        "message": f"{len(sims)} simulations found."
    }


# ── State Persistence ─────────────────────────────────────────

def _save_state(state: SimState, filepath: Path):
    """Save simulation state to JSON."""
    data = {
        "sim_id": state.sim_id,
        "scenario": state.scenario,
        "num_agents": state.num_agents,
        "num_rounds": state.num_rounds,
        "current_round": state.current_round,
        "status": state.status,
        "agents": [a.to_dict() for a in state.agents],
        "posts": [asdict(p) for p in state.posts],
        "events": state.events,
        "round_summaries": state.round_summaries,
        "report": state.report,
        "created_at": state.created_at,
        "completed_at": state.completed_at,
    }
    filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_state(filepath: Path) -> SimState:
    """Load simulation state from JSON."""
    data = json.loads(filepath.read_text(encoding="utf-8"))

    agents = []
    for ad in data.get("agents", []):
        agents.append(SimAgent(
            id=ad["id"], name=ad["name"], role=ad["role"],
            personality=ad["personality"], stance=ad["stance"],
            influence=ad["influence"], activity=ad["activity"],
            A=ad.get("A", 0.5), F=ad.get("F", 0.5), k=ad.get("k", 0.2),
            S=ad.get("S", 0.5), w=ad.get("w", 0.3),
            posts=ad.get("posts", []), interactions=ad.get("interactions", []),
        ))

    posts = []
    for pd in data.get("posts", []):
        posts.append(SimPost(
            id=pd["id"], author_id=pd["author_id"], author_name=pd["author_name"],
            content=pd["content"], round_num=pd["round_num"], timestamp=pd["timestamp"],
            likes=pd.get("likes", 0), comments=pd.get("comments", []),
            sentiment=pd.get("sentiment", 0.0),
        ))

    return SimState(
        sim_id=data["sim_id"], scenario=data["scenario"],
        num_agents=data["num_agents"], num_rounds=data["num_rounds"],
        current_round=data.get("current_round", 0), status=data.get("status", "created"),
        agents=agents, posts=posts, events=data.get("events", []),
        round_summaries=data.get("round_summaries", []),
        report=data.get("report", ""),
        created_at=data.get("created_at", ""), completed_at=data.get("completed_at", ""),
    )


# ── Tool Definitions ─────────────────────────────────────────

TOOLS = [
    {
        "name": "create_simulation",
        "description": "Create a swarm simulation with AI agents that have distinct personalities, stances, and PUT variables. Define a scenario and optional events to inject.",
        "parameters": {
            "scenario": "string — what to simulate (e.g., 'How will the AI agent market react to a new privacy regulation?')",
            "num_agents": "int — number of agents (default 10, max 30)",
            "num_rounds": "int — simulation rounds (default 5, max 15)",
            "events": "list — optional events to inject [{round: N, description: '...'}]",
        },
        "handler": create_simulation,
    },
    {
        "name": "run_simulation",
        "description": "Run a created simulation. Agents interact, post, comment, and react based on their personalities and the scenario. Produces a prediction report.",
        "parameters": {
            "sim_id": "string — simulation ID from create_simulation",
        },
        "handler": run_simulation,
    },
    {
        "name": "get_simulation_report",
        "description": "Get the prediction report from a completed simulation. Includes sentiment analysis, stakeholder map, predictions, and PUT analysis.",
        "parameters": {
            "sim_id": "string — simulation ID",
        },
        "handler": get_simulation_report,
    },
    {
        "name": "quick_predict",
        "description": "One-shot prediction: create simulation, run it, and get report in a single call. Fast but less control than step-by-step.",
        "parameters": {
            "scenario": "string — what to predict",
            "num_agents": "int — agents (default 8, max 20)",
            "num_rounds": "int — rounds (default 3, max 8)",
            "events": "list — optional events [{round: N, description: '...'}]",
        },
        "handler": quick_predict,
    },
    {
        "name": "list_simulations",
        "description": "List all simulations with status and stats.",
        "parameters": {},
        "handler": list_simulations,
    },
]
