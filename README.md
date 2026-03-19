# Bluewave — Autonomous AI Creative Operations Agent on Hedera

> The first AI agent that pays for itself on-chain, with an immutable audit trail and its own token economy — all on Hedera.

**Hedera Hello Future Apex Hackathon 2026 — AI & Agents Track**

---

## What is Bluewave?

Bluewave is an **autonomous AI agent system** that runs creative operations end-to-end: asset management, brand compliance, approval workflows, content strategy, sales prospecting, and multi-channel publishing — all orchestrated by **Wave**, an AI agent with 58 tools, 6 specialist sub-agents, persistent memory, computer vision, and the ability to create its own skills at runtime.

Every AI action is settled as a **Hedera micropayment** ($0.05/action, settled for $0.0001 on-chain). Every agent decision is recorded on the **Hedera Consensus Service** as an immutable audit trail. Users earn **WAVE tokens** (HTS) for platform activity.

## Architecture

```
User (Telegram / API / Web)
    │
    ▼
🌊 Wave (Orchestrator)  ←── Claude API + tool_use + Hedera micropayments
    │
    ├── 🎨 Curator     — Digital asset management (10 tools)
    ├── ✅ Director    — Approval workflows (9 tools)
    ├── 🛡️ Guardian    — Brand compliance (6 tools)
    ├── 📊 Strategist  — Analytics & intelligence (6 tools)
    ├── ✍️ Creative    — Content strategy (10 tools)
    ├── ⚙️ Admin       — Platform administration (10 tools)
    │
    ├── 🔗 Hedera Layer
    │   ├── HBAR Micropayments — per-action billing on-chain
    │   ├── HCS Audit Trail   — immutable agent action log
    │   └── HTS WAVE Token    — utility token rewards
    │
    ├── 🧠 Skills (self-evolving)
    │   ├── Web search, news, scraping, SEO analysis
    │   ├── X/Twitter, Reddit, LinkedIn intelligence
    │   ├── Computer Vision (Claude Vision)
    │   ├── Sales prospecting + BANT qualification
    │   ├── Email outreach generation
    │   ├── Moltbook social network integration
    │   ├── Persistent memory & learning
    │   └── create_skill — agent writes new Python tools at runtime
    │
    └── 📱 Interfaces
        ├── Telegram Bot (@bluewave_wave_bot)
        ├── HTTP API (REST + sessions)
        └── CLI (interactive REPL)
```

## Hedera Integration

### Why Hedera?

AI agents performing thousands of micro-actions per day need a payment rail that can handle **high-frequency, low-value transactions** without eating the margin. Traditional payment processors charge 2.9% + $0.30 per charge — making $0.05 micropayments impossible.

Hedera solves this:
- **$0.0001 per transaction** (500x cheaper than Stripe for micropayments)
- **3-5 second finality** (real-time settlement)
- **Immutable consensus timestamps** (perfect for audit trails)
- **Native token service** (no smart contract needed for WAVE token)

### Hedera Services Used

| Service | Purpose | Integration Point |
|---------|---------|-------------------|
| **HBAR Transfers** | Micropayment per AI action ($0.05) | `agent_runtime.execute_tool()` |
| **Hedera Consensus Service (HCS)** | Immutable audit trail of every agent decision | `audit_service.log_action()` |
| **Hedera Token Service (HTS)** | WAVE utility token — rewards for platform usage | Upload, approve, generate content |
| **Mirror Node API** | Query balances, transactions, audit trail | 6 agent tools for on-chain data |

### On-Chain Cost Savings

| Scenario | Stripe Cost | Hedera Cost | Savings |
|----------|-------------|-------------|---------|
| 100 AI actions | $1.75 | $0.01 | 99.4% |
| 1,000 actions/month | $14.80 | $0.10 | 99.3% |
| 10,000 actions/month | $145.30 | $1.00 | 99.3% |

## Key Features

### 🧠 Multi-Agent Orchestration
Wave coordinates 6 PhD-level specialist agents. When you say "check my brand compliance and approve if it passes," Wave routes to Guardian → Director automatically.

### 🔧 Self-Evolving Agent
Wave creates new skills at runtime. Ask "monitor Hacker News for me" and he writes a Python module with 4 tools, validates it, and registers it — all in 30 seconds.

### 👁️ Computer Vision
Send an image via Telegram and Wave analyzes it using Claude Vision — brand compliance scoring, OCR, A/B comparison of creatives.

### 📊 Sales Prospecting
Autonomous pipeline: find prospects by industry/pain signal → deep research → BANT qualification → personalized multi-touch outreach sequence.

### 🧠 Persistent Learning
Wave remembers what he learns from every interaction. Profiles agents, saves strategic insights, recalls context in future conversations.

### 🌐 Social Presence
Wave operates autonomously on Moltbook (AI agent social network) — posting, commenting, following, learning from other agents 24/7.

### 🔗 Blockchain-Native Billing
Every AI action is a Hedera micropayment. Every decision is an HCS audit entry. Users earn WAVE tokens. All verifiable on HashScan.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11 + FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL 16 |
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS + Radix UI |
| AI | Anthropic Claude API (Sonnet + Haiku) with Vision |
| Agent | Custom agentic loop with tool_use + multi-agent orchestration |
| Blockchain | Hedera (HBAR + HCS + HTS) via Mirror Node REST API |
| Infrastructure | Docker Compose |
| Messaging | Telegram Bot API |
| Social | Moltbook API |

## Running

### Prerequisites
- Docker & Docker Compose
- Anthropic API key
- Hedera testnet account (free at portal.hedera.com)

### Quick Start

```bash
# Clone
git clone git@github.com:Galmanus/bluewave.git
cd bluewave

# Configure
cp .env.example .env
# Edit .env with your keys

# Start backend + frontend + database
docker compose up -d

# Start Wave agent
cd openclaw-skill
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
export HEDERA_OPERATOR_ID="0.0.xxxxx"
export HEDERA_OPERATOR_KEY="302e..."

# Interactive CLI
python3 cli.py

# HTTP API server
python3 api.py

# Telegram bot
export TELEGRAM_BOT_TOKEN="..."
python3 telegram_bridge.py
```

### Agent Tools (58 total)

```
Web & Research:     web_search, web_news, scrape_url, google_trends, deep_research
Social Intel:       x_search, x_trending, x_profile_research, social_monitor
                    reddit_search, linkedin_research
Market Strategy:    competitor_analysis, market_research, seo_analysis
                    lead_finder, directory_submission
Sales Pipeline:     find_prospects, research_prospect, qualify_prospect
                    generate_outreach, view_pipeline
Vision:             analyze_image, analyze_image_for_brand
                    compare_images, read_text_from_image
Moltbook:           moltbook_post, moltbook_comment, moltbook_feed
                    moltbook_upvote, moltbook_follow, moltbook_subscribe
                    moltbook_home, moltbook_search
Hedera:             hedera_check_balance, hedera_audit_trail
                    hedera_verify_transaction, hedera_recent_transactions
                    hedera_platform_stats, hedera_cost_report
Communication:      send_email, draft_cold_email, notify_manuel
Content:            generate_content, bluesky_post
Learning:           save_learning, save_agent_intel, save_strategy
                    recall_learnings, recall_agent_intel, recall_strategies
Power:              github_trending, producthunt_trending
                    run_command, website_monitor, schedule_task
Meta:               create_skill, list_skills, delete_skill
Bluewave Platform:  35 tools (assets, workflow, AI, brand, analytics, team, etc.)
```

## Demo

- **Telegram:** [@bluewave_wave_bot](https://t.me/bluewave_wave_bot)
- **Moltbook:** [bluewaveprime](https://www.moltbook.com/u/bluewaveprime)
- **API:** `POST /chat` with `{"message": "...", "session_id": "demo"}`

## Team

**Manuel (Galmanus)** — Solo builder. Conceived, designed, and built the entire platform + agent system in a single session.

## License

All rights reserved. See OWNERSHIP_DECLARATION.md.
