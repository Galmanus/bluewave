---
name: bluewave
description: "Sistema multi-agente de operações criativas e inteligência estratégica — 1 orquestrador + 10 agentes especialistas PhD em assets, aprovações, compliance, analytics, conteúdo, admin, legal, financeiro, segurança, blockchain e análise de risco."
homepage: https://bluewave.app
user-invocable: true
metadata: {"openclaw":{"requires":{"env":["BLUEWAVE_API_URL","BLUEWAVE_API_KEY"]},"primaryEnv":"BLUEWAVE_API_KEY","emoji":"🌊"}}
---

# 🌊 Bluewave — Sistema Multi-Agente de Inteligência Criativa & Estratégica

Conecte seu workspace Bluewave ao OpenClaw. Um orquestrador central (Wave) classifica intenções e delega para 10 agentes especialistas PhD — cada um com domínio profundo em assets, aprovações, compliance, analytics, conteúdo, administração, jurídico, financeiro, segurança cibernética, blockchain ou análise de risco extrema.

## Configuração

1. No Bluewave (admin), vá em **Settings → API Keys** e crie uma nova chave.
2. Configure as variáveis de ambiente:
   ```bash
   export BLUEWAVE_API_URL="https://your-bluewave-instance.com/api/v1"
   export BLUEWAVE_API_KEY="bw_your_api_key_here"
   ```

## Agentes Especialistas

O sistema opera com 1 orquestrador + 10 especialistas. Cada agente tem um soul prompt dedicado, ferramentas restritas ao seu domínio e personalidade própria.

### 🌊 Wave — Orquestrador Principal
Ponto de entrada conversacional. Classifica intenções e delega tarefas complexas para o especialista adequado.

### 🎨 Curator — Assets Digitais
PhD em Ciência da Informação. Gestão, catalogação, busca e ciclo de vida de assets de mídia.

### ✅ Director — Workflow de Aprovação
PhD em Gestão de Operações. Automação de processos e tomada de decisão para workflows.

### 🛡️ Guardian — Brand Compliance
PhD em Comunicação Visual. Semiótica de marca, color science e integridade visual.

### 📊 Strategist — Analytics
PhD em Business Analytics. Marketing analytics, ROI e data storytelling.

### ✍️ Creative — Estratégia de Conteúdo
PhD em Comunicação e Marketing Digital. Content strategy e brand storytelling.

### ⚙️ Admin — Administração
PhD em Sistemas de Informação. SaaS platform administration, IAM e segurança.

### ⚖️ Legal — Inteligência Jurídica & IP
PhD em Direito Empresarial. Proteção de IP, compliance (LGPD/GDPR), regulação de crypto/AI e estratégia de negociação via framework PUT.

### 💰 Financial — Revenue Ops & Growth
PhD em Finanças Corporativas. Unit economics, precificação dinâmica, tesouraria multi-moeda (HBAR/USDT) e modelagem de flywheel de crescimento.

### 🛡️ Security — Auditoria & Hardening
Especialista em Cibersegurança (MITRE/OWASP). Identifica vulnerabilidades, audita infraestrutura e recomenda hardening contra ataques.

### ⛓️ Blockchain — Smart Contracts & Web3
Arquiteto de Blockchain. Auditoria de smart contracts (Solidity/Rust), segurança Hedera EVM e análise de protocolos DeFi.

### 🗡️ Il Traditore — Risco Extremo & Pre-Mortem
O Adversário Interno. Institucionaliza a sabotagem para encontrar falhas catastróficas e simular contra-ataques antes da execução.

## Comandos Principais

### 🎨 Curator — Assets
- **Upload:** "Upload this to Bluewave"
- **Busca:** "Find assets about summer campaign"
- **Exportar:** "Export these 5 assets as ZIP"

### ✅ Director — Workflow
- **Submeter:** "Submit [nome] for approval"
- **Aprovar:** "Approve all pending assets" (Admin)
- **Stats:** "Show workflow stats"

### 🛡️ Guardian — Compliance
- **Verificar:** "Check compliance on [asset]"
- **Guidelines:** "Show our brand guidelines"
- **Relatório:** "Generate a compliance report"

### ⚖️ Legal — Jurídico
- **Pesquisa:** "Legal research on AI regulation in Brazil"
- **Contrato:** "Analyze this contract for risks"
- **Compliance:** "Run an LGPD compliance check"

### 💰 Financial — Financeiro
- **Unit Economics:** "Show unit economics for our creative services"
- **Forecast:** "Revenue forecast for the next 6 months"
- **Treasury:** "Show current treasury status (HBAR/USDT)"

### 🗡️ Il Traditore — Risco
- **Pre-Mortem:** "Sabotage our summer campaign strategy — what can go wrong?"
- **Red Team:** "Critique our new pricing model from an adversary perspective"

## Referência de Tools (260+)

O sistema integra mais de 260 ferramentas especializadas, incluindo:
- **Web Search & Intelligence:** `web_search`, `deep_research`, `scrape_url`, `google_trends`.
- **Social & News:** `x_search`, `reddit_search`, `hn_top_stories`, `producthunt_trending`.
- **Blockchain:** `hedera_check_balance`, `starknet_deploy`, `privacy_audit_proposal`.
- **Revenue:** `pricing_optimizer`, `cac_ltv_analysis`, `profitability_ranking`.
- **Legal:** `contract_analyzer`, `ip_strategy`, `regulatory_monitor`.
- **Core Bluewave:** `bluewave_upload_asset`, `bluewave_approve_asset`, `bluewave_check_compliance`.

**Autenticação:** Todas as requisições usam o header `X-API-Key: $BLUEWAVE_API_KEY`.
