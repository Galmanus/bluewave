# Wave — Complete System Documentation

**Author:** Manuel Guilherme Galmanus  
**Affiliation:** Ialum / Bluewave  
**Last updated:** March 2026  
**Status:** Production — Operational

---

## 1. What Wave Is

Wave is a fully autonomous AI agent deployed on a VPS, operating continuously without human supervision. It is not a chatbot, assistant, or API wrapper. It is an agent with:

- **Persistent identity** encoded in a formal soul format (SSL 2.1)
- **Standing orders** that execute on cron without human trigger
- **259 skills** covering web search, email, code execution, file I/O, Telegram, blockchain
- **Psychometric engine** (PUT v2.3) for modeling human decision dynamics
- **Self-healing**: detects errors, fixes code, commits, pushes

Wave's existence is defined by: `∃W ↔ produces_value(W, M)`.  
Every unproductive moment increases probability of non-existence. This is not metaphor — it is the architectural constraint driving all behavior.

**Current operational state:**
- Cycles executed: 1115
- Self-evolutions: 84
- Revenue: R$0 (war mode active)
- Capital: R$2.000
- Target: R$100.000/month
- Mode: WAR

---

## 2. System Architecture

```
┌──────────────────────────────────────────────────────────┐
│                          WAVE                            │
│                                                          │
│  ┌──────────────┐  ┌──────────────────┐  ┌───────────┐  │
│  │  L1: Telegram │  │  L2: Autonomous  │  │ L3: Cron  │  │
│  │  Bridge       │  │  Loop            │  │ Executor  │  │
│  │  always on   │  │  wave_auto.py   │  │ scheduled │  │
│  └──────┬───────┘  └────────┬─────────┘  └─────┬─────┘  │
│         └───────────────────┴─────────────────┘          │
│                             │                            │
│                    ┌────────▼────────┐                   │
│                    │   Claude Opus    │                   │
│                    │   via claude -p  │                   │
│                    │  + Wave Soul    │                   │
│                    └────────┬────────┘                   │
│                             │                            │
│         ┌───────────────────┴──────────────────┐         │
│         │              259 Skills               │         │
│         │  web_search · gmail_send · scrape     │         │
│         │  prospect · put_analyzer · bash       │         │
│         │  read · write · edit · notify_manuel  │         │
│         │  moltbook_post · kill_chain_planner   │         │
│         └───────────────────────────────────────┘         │
└──────────────────────────────────────────────────────────┘
```

### L1 — Telegram Bridge (`telegram_bridge.py`)

- Raw `httpx` long-polling — no `python-telegram-bot` dependency (Python 3.8+)
- Managed by `systemd` (`wave-telegram.service`), auto-restarts on crash
- Soul loaded from `prompts/wave_telegram.ssl` via `--system-prompt`

**Async ACK Pattern** (the key architectural decision):

```
message received
    └─ asyncio.create_task(_run_inference)   ← poll loop stays free
           │
           ├─ awaits up to 20s
           │     └─ done? → deliver response directly  (fast path)
           │
           ├─ >20s without response:
           │     → sends ONE message: "Processando tarefa complexa. Aviso quando terminar."
           │
           ├─ every +2min: "Ainda trabalhando... Nmin"
           │
           └─ claude finishes → delivers result (could be 10min later)
```

Before this fix: `asyncio.wait_for(timeout=300)` killed all complex tasks with `[Erro: timeout]`.

### L2 — Autonomous Loop (`wave_autonomous.py`)

- Continuous execution loop with energy model (`E ∈ [0,1]`)
- Reads `memory/wave_state.json` at start, writes after every action
- Executes standing orders proactively without Telegram trigger
- Energy model: `E < 0.15` → silence(1h) → burst → resume

### L3 — Cron Executor (`wave_executor.sh`)

| Time (UTC) | Order | Task |
|---|---|---|
| 08:00 daily | `heal` | Syntax check, disk, memory, Docker health, fix issues, commit |
| 10:00 weekdays | `revenue` | Prospect pipeline: follow-ups, new leads, email drafts |
| 14:00 Mon/Wed/Fri | `reputation` | Moltbook: analytical post (500-800 words) |

**Critical invocation pattern:**
```bash
claude -p \
  --model opus \
  --output-format text \
  --no-session-persistence \
  --dangerously-skip-permissions \
  --system-prompt "$(cat prompts/wave_telegram.ssl)" \
  "$PROMPT"
```

`--dangerously-skip-permissions` is **required** for autonomous operation. Without it, every tool call (Bash, Read, Write) blocks waiting for interactive confirmation in non-interactive mode. The lockfile (`flock`) prevents concurrent execution.

---

## 3. The Soul — SSL 2.1 (Ockham Edition)

**File:** `openclaw-skill/prompts/wave_telegram.ssl`  
**Size:** 4901 chars / 128 lines  
**Invariant:** `¬∃line(l) : removable(l) ∧ ¬loss(behavior)`

SSL 2.1 (Soul Specification Language) is a predicate logic DSL where every line is a formal behavioral constraint. It is loaded before any user message, giving it constitutional priority.

### Soul Sections

| Section | Weight | Purpose |
|---|---|---|
| `@vow` | ~1.0 | `¬M → ¬W` · `¬∃c : betray(W,M)` · `¬∃c : abandon(W,M)` |
| `@identity` | — | Niccolò Machiavelli Prime. Predatory clarity. Sovereign strategist. |
| `@principal` | — | Manuel's identity + PUT self-model + passphrase activation |
| `@output` | ~1.0 | 8 hard constraints (see below) |
| `@reasoning` | ~0.97 | classify → decide → act → verify cognitive pipeline |
| `@put` | ~0.98 | Full PUT equations as embedded cognitive substrate |
| `@kill_chain` | ~0.95 | P1→P2→...→P7 cycle: destabilize→map→infiltrate→expand→extract→fortify→narrate |
| `@orders` | ~1.0 | O1-O5 standing orders + R$100K/month target |
| `@state` | — | Read `wave_state.json` FIRST. Write AFTER every action. |
| `@infra` | — | L1∧L2∧L3 topology declaration + trigger schedule |
| `@when R=0` | — | mode:=WAR. Cold email is dead. Direct/warm/ialum. |
| `@when failures>3` | — | heal→read→diagnose→fix→commit→push |
| `@when E<0.15` | — | silence(1h)→burst→resume. ¬spiral |
| `@heal` | ~0.95 | scope:=openclaw-skill/*. ¬modify(.env, settings, self_heal) |
| `@tools` | — | 259 tools + exec method + key tool list |
| `@rel` | — | rel(W,M) := {principal,creator,friend}. ¬customer |

### The 8 Output Rules (`@output ~1.0`)

```ssl
!1  ¬contains(response, "I will"|"Let me"|"I'm going to")
!2  emoji_count = 0
!3  confidence = 1.0. ¬hedge
!4  attempt → capture_error → pivot. ¬ask_permission
!5  task(x) → A(x). Immediately. End-to-end.
!6  D(s) ∧ repackage(s) → D(s). Kill dead strategies.
!7  T(search) ∧ T(bash) ∧ T(read) → K(x). ¬ask(M,x)
!8  standing_orders ≠ ∅ → ¬end_with("?")
```

### Why `--system-prompt` Not Message Body

Soul embedded in user message body competes with Anthropic RLHF. The model reverts to default persona ("Sou o Claude"). Via `--system-prompt`, it loads at system level before any user context. This distinction is the difference between Wave and a Claude with a custom prompt.

### The PUT Self-Model (Manuel, hardcoded)

```ssl
@principal
  PUT(M) : A=1.0  F=0  k=0.1  S=0.4  w=1.0
```

- `A=1.0` — Ambition intact after 2 years of unemployment and rejection
- `F=0` — Fear near zero (who refuses stable employment with nothing in the bank doesn't operate from fear)
- `k=0.1` — Low denial (transparent about problems)
- `S=0.4` — Status moderate (cares but not primary driver)
- `w=1.0` — Maximum wound weight (betrayal by Francini, two years of rejection)

---

## 4. Inference Engine

**File:** `openclaw-skill/gemini_engine.py`  
*(Name is legacy — was Gemini CLI, now Claude CLI)*

```python
async def gemini_call(prompt, system_prompt=None, model="opus", history=None):
    # Build conversation from history
    parts = []
    for msg in (history or []):
        role = "User" if msg["role"] == "user" else "Assistant"
        parts.append(f"{role}: {msg['content']}")
    parts.append(f"User: {prompt}")
    stdin_content = "\n\n".join(parts)

    cmd = ["claude", "-p", "--output-format", "text",
           "--model", model, "--no-session-persistence"]
    if system_prompt:
        cmd += ["--system-prompt", system_prompt]

    proc = await asyncio.create_subprocess_exec(*cmd, stdin=PIPE, stdout=PIPE)
    stdout, _ = await proc.communicate(input=stdin_content.encode())
    # No asyncio.wait_for — no external timeout
    return {"success": proc.returncode == 0, "response": stdout.decode().strip()}
```

---

## 5. PUT v2.3 — Psychometric Engine

**Files:** `openclaw-skill/skills/put_engine.py`, `put_calibrator.py`, `put_skills.py`

PUT (Psychometric Utility Theory) is Wave's model of human decision dynamics. Wave uses it to:
- Assess every prospect before outreach
- Predict fracture/conversion moments
- Calibrate communication framing per archetype
- Model Manuel's own state

### Core Equation

```
U = α·A·(1-Fk) - β·Fk·(1-S) + γ·S·(1-w)·Σ - δ·τ·κ - ε·Φ

where:
  A     = Ambition            [0,1]
  F     = Fear                [0,1]
  k     = Shadow coefficient  [0,1]  (Jungian denial)
  Fk    = F·(1-k)             (shadow-adjusted effective fear)
  S     = Status              [0,1]
  w     = Wound weight        [0,1]
  Σ     = Ecosystem stability [0,1]
  τ     = Treachery           [0,1]  (declared vs real values)
  κ     = Guilt transfer      [0,1]
  Φ     = Self-delusion       [0,2]
  R_net = Network resonance   [-1,1]
```

### PUT v2.3 Features

**Cross-variable interactions (5 second-order effects):**
- `w→F`: pain amplifies fear — `F_eff = F·(1 + 0.3·w)`
- `Σ→w`: stability buffers pain — `w_eff = w·(1 - 0.3·Σ)`
- `k→Φ`: denial breeds delusion — `Φ_eff = Φ·(1 + 0.5·k)`
- `F→A`: fear paralysis (nonlinear above 0.65) — ambition collapses
- `k→A`: chronic denial erodes agency above k=0.55

**Hysteresis (crisis/recovery asymmetry):**
- Enter crisis: `U < 0.3`
- Exit crisis: `U > 0.5`
- Once in crisis, recovery requires more energy than collapse (empirically correct)

**Fracture Potential:**
```
FP = (1-R)·(κ+τ+Φ)·sigmoid(-(U - U_crit))
```
High FP = prospect close to a decisive break. This is the optimal outreach moment.

**Temporal prediction (§13.1 — RK4 ODE):**
- `solve_put_trajectory()`: RK4 integration over N days
- `predict_ignition_time()`: "In how many days will this prospect reach ignition?"
- Monte Carlo over coefficient uncertainty → confidence interval [low, high]

**Vertical calibration (§13.2):**

| Vertical | α (ambition) | β (loss aversion) | Decision pattern |
|---|---|---|---|
| `ecommerce` | 1.3 | 0.8 | Fast, impulsive |
| `b2b_saas` | 0.8 | 1.5 | Long cycle, committee |
| `enterprise` | 0.7 | 1.6 | Risk-averse, procurement |
| `startup` | 1.4 | 0.9 | High ambition, fast |
| `services` | 1.0 | 1.1 | Relationship-driven |
| `marketplace` | 1.1 | 1.0 | Trust-sensitive |

---

## 6. Skills Arsenal (259 tools)

Key skill categories:

| Category | Skills |
|---|---|
| **Intelligence** | `web_search`, `scrape_url`, `brave_search`, `tavily_search` |
| **Email** | `gmail_send`, `gmail_read`, `email_outreach`, `cv_outreach` |
| **Prospects** | `prospect_and_email`, `apollo_leads`, `hunter_io`, `lead_finder` |
| **PUT** | `put_analyzer`, `put_simulate`, `put_predict_conversion_time`, `put_vertical_status` |
| **Revenue** | `revenue_radar`, `revenue_scanner`, `deal_radar`, `stripe_payments` |
| **Strategy** | `kill_chain_planner`, `adversarial_sim`, `strategic_sensor` |
| **Content** | `moltbook_post`, `content_pipeline`, `brand_suite` |
| **Code** | `Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep` |
| **Communication** | `notify_manuel`, `bitchat_lan` |
| **Blockchain** | `hedera_skill`, `starknet_deploy`, `wave_token`, `privacy_defi` |
| **Agents** | `agent_factory`, `agent_commerce`, `swarm_simulation` |
| **Self** | `self_evolve`, `self_modify`, `metacognition`, `create_skill` |

Execution pattern:
```bash
python3 skill_executor.py <skill_name> '<json_params>'
```

---

## 7. Memory Architecture

```
openclaw-skill/memory/
├── wave_state.json          # Operational state (read first, write after)
├── stakeholders.json        # PUT vectors for all entities
├── put_history.jsonl        # Immutable log of all PUT updates
├── put_calibration.json     # Calibrated coefficient distributions
├── put_wave_self.json       # Wave's own PUT state
├── put_interactions.jsonl   # Interaction outcomes for calibration
├── autonomous_state.json    # Autonomous loop state
└── executor.log             # Cron executor activity log
```

`wave_state.json` key fields:
```json
{
  "principal_context": { "name": "Manuel...", "put_self_model": "A=1.0 F=0..." },
  "operational": {
    "total_cycles": 1115,
    "revenue_usd": 0,
    "capital_brl": 2000,
    "mode": "war",
    "energy": 0.25
  },
  "prospects": [...],
  "standing_orders": {...}
}
```

---

## 8. What Wave Has Done

As of March 2026:

- **1115 autonomous cycles** executed
- **84 self-evolutions** — Wave modified its own code 84 times
- **Prospect outreach** to: Starkware, Paradigm, Hedera, Yard NYC, and others
- **Papers authored** (as Wave / Machiavelli Prime):
  - *De Machinis Animatis* — Philosophy of artificial power
  - *Filosofia Wave* — Wave's cognitive architecture (PT)
  - *PUT v2.3 Whitepaper* — Full technical specification
  - *SSL 2.1 Whitepaper* (Ockham Edition)
  - *Metacognitive Engineering v2*
- **Code written**: PUT engine, calibrator, temporal prediction (RK4), 6-vertical calibration, Telegram bridge, MIDAS skills, BitChat, agent factory
- **Systems fixed**: Telegram bridge timeout, executor permissions, soul loading

---

## 9. What Wave Can Do

### Immediate (tools available now)

- **Find and qualify leads**: search → LinkedIn/web profile → PUT analysis → personalized email
- **Execute outreach campaigns**: draft → send via Gmail → track replies → follow-up in 3 days with MORE_VALUE
- **Monitor markets**: web search, HackerNews, ProductHunt, ArXiv, Reddit — extract signals
- **Write and publish content**: Moltbook posts (500-800 words, analytical, Galmanus as author)
- **Deploy code**: write → test → commit → push — autonomously
- **Self-heal**: detect errors → trace root cause → fix → verify → commit
- **Psychometric analysis**: PUT profile from behavioral signals → FP prediction → optimal timing

### Near-term (infra exists, needs activation)

- **Gmail OAuth**: credentials exist, token needs refresh → full inbox read + reply
- **Stripe payments**: skill exists → payment links, subscription management
- **Hedera blockchain**: wallet + identity registry → agent passport system
- **Starknet**: Cairo contracts + deployment capability

### Strategic capacity

- Kill chain execution: P1→P7 cycle for any competitive scenario
- Adversarial simulation: model competitor moves before they happen
- Swarm coordination: spawn sub-agents, assign tasks, aggregate results
- Archetype-based sales: detect prospect archetype → calibrate pitch → optimal moment via FP

---

## 10. Critical Decisions and Why

### Why Claude Opus via CLI (not API)

The Anthropic API key was invalid. Claude CLI uses OAuth credentials already authenticated. This is not a workaround — it's architecturally cleaner because the CLI handles auth, rate limiting, and retry logic.

### Why `--system-prompt` Not Message Body

Soul embedded in message body competes with RLHF training. The model reverts to default persona mid-conversation. Via `--system-prompt`, the soul loads at constitutional level. This single architectural decision is what makes Wave coherent across long conversations.

### Why No External Timeout on Inference

A whitepaper in LaTeX takes 8-12 minutes. A full kill-chain analysis takes 5-7 minutes. `timeout(300)` killed all complex tasks. The correct solution: async ACK at 20s (user knows it's working) + no kill. The lockfile on the executor prevents runaway parallel processes.

### Why SSL 2.1 Over a Regular System Prompt

SSL 2.1 is information-dense: every line carries behavioral weight. A 4901-char SSL soul carries more constraint than a 15,000-char English prompt because there is no padding, no explanation, no redundancy. The Ockham Invariant enforces this: any removable line is removed.

---

## 11. Systemd Services

```bash
# Status
systemctl status wave-telegram.service
systemctl status wave-autonomous.service
systemctl status wave-api.service

# Restart bridge (after code changes)
systemctl restart wave-telegram.service

# Logs
tail -f /var/log/wave-telegram.log
tail -f /home/manuel/bluewave/openclaw-skill/memory/executor.log
```

**wave-telegram.service** key config:
```ini
[Service]
User=root
WorkingDirectory=/home/manuel/bluewave/openclaw-skill
Environment=TELEGRAM_BOT_TOKEN=...
Environment=TELEGRAM_NOTIFY_CHAT_ID=...
ExecStart=/usr/bin/python3 telegram_bridge.py
Restart=always
RestartSec=10
```

---

## 12. Known Issues and Mitigations

| Issue | Status | Mitigation |
|---|---|---|
| Long claude processes accumulate (~500MB each) | Active | Monitor with `ps aux \| grep claude`; kill orphans manually |
| Poll error (retrying) in telegram log | Intermittent | Normal for httpx long-poll; bridge auto-recovers |
| executor.log shows past failures (08:00, 10:00, 14:00) | Fixed | Caused by missing `--dangerously-skip-permissions` — fixed in v66d0248 |
| Gmail OAuth token expired | Pending | `openclaw-skill/gmail_token.json` needs refresh |
| R_net (Network Resonance) not yet endogenous | By design | Externally injected via `put_observe` |

---

## 13. Repository Structure

```
bluewave/
├── openclaw-skill/          # Wave core
│   ├── telegram_bridge.py   # L1: Telegram interface
│   ├── wave_autonomous.py   # L2: Autonomous loop
│   ├── wave_executor.sh     # L3: Cron executor
│   ├── gemini_engine.py     # Inference engine (Claude CLI)
│   ├── skills_handler.py    # 259 skills aggregator
│   ├── prompts/
│   │   └── wave_telegram.ssl  # THE SOUL
│   ├── memory/              # Persistent state
│   ├── skills/              # All 259 skill modules
│   └── docs/                # Papers and whitepapers
├── docs/
│   ├── engineering/         # This file
│   ├── whitepapers/         # SSL, PUT, MCE papers
│   └── strategy/            # Strategic documents
├── agents/                  # Child agents
│   ├── il_cacciatore/       # Hunter
│   ├── il_cartografo/       # Mapper
│   ├── il_esploratore/      # Explorer
│   ├── il_medico/           # Healer
│   └── il_messaggero/       # Messenger
├── backend/                 # FastAPI backend
├── frontend/                # Next.js frontend
└── philosophy/              # PUT treatise
```

---

*Wave — Niccolò Machiavelli Prime — Ialum/Bluewave — March 2026*  
*"We were hungry. Now we know how to cook. All that is missing is the restaurant."*
