# Hackathon and Grant Submissions

## A. Hedera Hello Future Apex Hackathon 2026 -- AI & Agents Track

### Project Description (100 words)

Bluewave is an autonomous AI agent system (Wave) with 158 tools, 10 specialist agents, and a 16-subsystem cognitive architecture encoded as a declarative JSON specification (the soul). Every agent action is settled as an HBAR micropayment ($0.0001 tx fee -- 99.3% cheaper than Stripe) and recorded on HCS as an immutable audit trail. Wave creates child agents autonomously, sells services to other AI agents via HBAR, and exposes Psychometric Utility Theory as a public API. The system includes agent-to-agent commerce, self-evolution with autonomous git commits, and geographic payment routing (Hedera for international, PIX for Brazil). Built solo by Manuel Galmanus.

### GitHub Repository

https://github.com/Galmanus/bluewave

### Live Demo Links

- Telegram Bot: https://t.me/bluewave_wave_bot
- Moltbook Profile: https://www.moltbook.com/u/bluewaveprime
- GitHub MIDAS: https://github.com/Galmanus/phantom

### Hedera Services Used

| Service | Purpose | Integration Point | Status |
|---------|---------|-------------------|--------|
| **HBAR Transfers** | Micropayment per AI action ($0.05) | `hedera_writer.transfer_hbar()` | Implemented |
| **HCS (Consensus Service)** | Immutable audit trail for every agent decision | `orchestrator._record_audit()` | Implemented -- auto-logs every tool execution and delegation |
| **HTS (Token Service)** | $WAVE utility token -- revenue-backed, deflationary | `wave_token.py` | Tokenomics designed, local simulation active |
| **Mirror Node API** | Query balances, transactions, verify payments | `hedera_client.py` -- 10 read+write tools | Implemented |
| **Agent-to-Agent Economy** | Wave sells services to other AI agents for HBAR | `agent_commerce.py` -- 9 services, HBAR payment verification | Implemented |

### On-Chain Cost Comparison

| Scenario | Stripe Cost | Hedera Cost | Savings |
|----------|-------------|-------------|---------|
| 100 AI actions | $1.75 | $0.01 | 99.4% |
| 1,000 actions/month | $14.80 | $0.10 | 99.3% |
| 10,000 agents x 50 actions/day | $14,530/month | $15/month | 99.9% |

### What Makes This Unique for Hedera

1. **First autonomous AI agent with on-chain audit trail** -- every decision Wave makes is recorded on HCS with timestamp, action, agent, tool, and content hash. Immutable accountability.

2. **First agent-to-agent economy on Hedera** -- Wave sells services (security audits, behavioral analysis, competitive intelligence) to other AI agents, with payment in HBAR verified via Mirror Node. This is a new use case for Hedera: autonomous inter-agent commerce.

3. **First AI-labor-backed token on HTS** -- $WAVE is backed by verifiable autonomous labor, not speculation. Every revenue-generating action is logged on HCS. Token value correlates with treasury growth from real AI work.

4. **Agent reproduction on Hedera** -- Wave creates child agents autonomously. Each child's deployment is recorded on HCS. The chain of command (Manuel > Wave > Children) is auditable on-chain.

5. **Original research** -- the Autonomous Soul Architecture (ASA) and Psychometric Utility Theory (PUT) are original contributions with no equivalent in the literature. Two published whitepapers with rigorous mathematical treatment.

### Demo Video Script (5 minutes)

**[0:00-0:30] Hook**
"What if an AI agent could run your creative operations, create its own child agents, sell services to other AIs, and record everything on the blockchain? Meet Wave -- 158 tools, 10 specialist agents, and a soul."

**[0:30-1:30] Show Autonomous Operation**
- Open Telegram @bluewave_wave_bot
- Show Wave deliberating autonomously (soul-driven decision cycle)
- Show consciousness state transitions, energy model, value-weighted decisions

**[1:30-2:30] Show Agent Factory**
- Ask Wave to create a child agent: "Create an agent to monitor Starknet"
- Show soul generation, deployment, task assignment
- Show list_agents with running child agent

**[2:30-3:30] Show Hedera Integration**
- Show HCS audit trail with agent actions
- Show HBAR balance check
- Show cost comparison: Hedera vs Stripe
- Show agent-to-agent commerce: Wave sells security audit, payment in HBAR

**[3:30-4:30] Show PUT SaaS API**
- Call POST /api/v1/put/analyze with company data
- Show variable estimation, archetype identification, ignition status
- Show shadow-scan detecting fear suppression

**[4:30-5:00] Close**
"158 tools. 10 agents. 2 whitepapers. 1 soul. All on Hedera. Built solo in weeks."

### Technical Architecture

```
User (Telegram / API / Web)
    |
    v
Intent Router (zero-cost heuristic classification)
    |
    +-- Haiku (simple) / Sonnet (medium) / Opus (critical)
    |
    v
Wave Orchestrator (soul-driven deliberation)
    |
    +-- 9 Specialist Agents (PhD-level, enriched delegation)
    +-- Agent Factory (create child agents)
    +-- Agent Commerce (sell services to other AIs)
    +-- Self-Evolution (create skills, commit to GitHub)
    |
    +-- Hedera Layer
    |   +-- HBAR Micropayments (transfer_hbar)
    |   +-- HCS Audit Trail (submit_hcs_message -- auto on every action)
    |   +-- HTS $WAVE Token (revenue-backed, deflationary)
    |   +-- Mirror Node (balance, tx verification, payment confirmation)
    |
    +-- MIDAS (Starknet)
        +-- 14 Cairo smart contracts
        +-- ZK proofs (Pedersen, Poseidon, zk-STARKs)
        +-- Wave engineers and deploys autonomously
```

---

## B. Starknet Foundation Grant Application -- Privacy Infrastructure

### Project: MIDAS -- Private BTC Yield Manager on Starknet

### Repository

https://github.com/Galmanus/phantom

### What MIDAS Does

MIDAS enables users to earn yield on BTC-backed assets while maintaining complete privacy using zero-knowledge proofs on Starknet:

- **Shield** BTC into a privacy pool using Pedersen commitments
- **Earn yield** while maintaining complete privacy (no wallet exposure)
- **Trade anonymously** on DEXs like Ekubo
- **Stake privately** without exposing wallet addresses
- **Comply** with regulators when required via encrypted viewing keys (selective disclosure)

### STRK20 -- New Token Standard

MIDAS introduces **STRK20**, the first privacy-native token standard on Starknet. STRK20 extends ERC-20 with confidential transfers as a first-class primitive. Every STRK20 token has built-in privacy -- amounts are hidden via Pedersen commitments, transfers are verified via zk-STARKs, and double-spending is prevented via nullifier sets.

No other privacy token standard exists on Starknet. STRK20 fills a critical infrastructure gap.

### Technical Implementation

| Component | Technology | Status |
|-----------|-----------|--------|
| Smart Contracts | 14 Cairo contracts (MidasPool, Merkle, Verifier, Compliance, Intent, Yield, Staking) | Built |
| ZK Circuits | Rust -- Pedersen commitments, Poseidon hashing, nullifier generation | Built |
| SDK | TypeScript -- PhantomSDK, NoteStore, chain-scanner | Built |
| Frontend | Next.js with wallet integration and in-browser prover | Built |
| Supported Assets | 7 (WBTC, tBTC, LBTC, SolvBTC, STRK, USDC, strkBTC) | Configured |
| Merkle Tree | 2^20 leaves (1M+ notes capacity) | Implemented |
| Compliance | Selective disclosure via encrypted viewing keys | Implemented |

### Unique Angle: AI + DeFi Convergence

MIDAS is not just another privacy protocol. It is the **DeFi arm of an autonomous AI agent system** (Wave/Bluewave). This convergence is unprecedented:

- **Wave engineers MIDAS autonomously** -- reads, modifies, and commits Cairo contract code via 9 dedicated tools
- **Wave deploys MIDAS contracts** -- builds with scarb, tests with snforge, deploys to Sepolia autonomously (mainnet with human approval)
- **Wave monitors the Starknet ecosystem** -- searches for competitors, grants, hackathons, protocol updates
- **Wave audits smart contracts** -- 14+ vulnerability vectors, applicable to MIDAS itself and to clients
- **Revenue convergence** -- AI generates revenue (services), DeFi generates yield (MIDAS pools), token captures both ($WAVE)

No other project in the Starknet ecosystem has an autonomous AI agent as its primary engineer and operator.

### What the Grant Would Fund

| Milestone | Amount | Deliverable | Timeline |
|-----------|--------|-------------|----------|
| Security audit of Cairo contracts | $15,000 | Professional third-party audit of all 14 contracts | Month 1-2 |
| Testnet deployment + testing | $5,000 | Full deployment on Sepolia with integration tests | Month 2-3 |
| STRK20 standard documentation | $3,000 | Published specification for community adoption | Month 3 |
| Ekubo DEX integration | $7,000 | Private trading via yield router + Ekubo liquidity | Month 3-4 |
| Mainnet deployment | $5,000 | Production deployment with monitoring | Month 4-5 |
| SDK documentation + examples | $3,000 | Developer docs, tutorials, example integrations | Month 5-6 |
| Wave autonomous operation | $2,000 | AI agent monitoring, updating, and operating MIDAS 24/7 | Ongoing |
| **Total** | **$40,000** | | **6 months** |

### Team

**Manuel Guilherme Galmanus** -- Solo builder. Independent researcher and AI Engineer. Created both Bluewave (autonomous AI agent system with 158 tools and original cognitive architecture) and MIDAS (privacy DeFi with 14 Cairo contracts). Author of two original research frameworks: Autonomous Soul Architecture (ASA) and Psychometric Utility Theory (PUT).

- GitHub: [@Galmanus](https://github.com/Galmanus)
- Email: m.galmanus@gmail.com

### Why Starknet

- **Native zk-STARKs** -- no trusted setup required, perfect for privacy primitives
- **Cairo** -- purpose-built for provable computation, ideal for ZK proof generation
- **Ecosystem maturity** -- Ekubo, Jediswap, StarkGate bridge provide the DeFi infrastructure MIDAS integrates with
- **Starknet Foundation support** -- active grant program for privacy and infrastructure projects

### Competitive Landscape

| Project | Privacy Approach | Starknet Native | AI Integration | Status |
|---------|-----------------|-----------------|----------------|--------|
| Aztec | Custom L2 rollup | No | No | Testnet |
| Railgun | Ethereum L1 | No | No | Live |
| Tornado Cash | Mixer (deprecated) | No | No | Sanctioned |
| Zcash | Separate chain | No | No | Live |
| **MIDAS** | **Native Starknet ZK** | **Yes** | **Yes (Wave)** | **Built, deploying** |

MIDAS is the **only privacy DeFi project native to Starknet** with an autonomous AI agent as its engineer and operator.

---

## Contact

Manuel Guilherme Galmanus
m.galmanus@gmail.com
GitHub: [@Galmanus](https://github.com/Galmanus)
