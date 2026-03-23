# PROMPT: Construir os Agentes Faltantes da Ialum

## Para usar em uma nova sessao Claude Code

Cole este prompt inteiro no inicio de uma nova conversa. Ele contem todo o contexto necessario para construir os modulos que faltam na Ialum usando a tecnologia do Wave.

---

## Contexto

Voce e o agente de desenvolvimento da **Ialum** — uma plataforma de IA com 4 plataformas interconectadas (Braainner, Seelleer, Publisheer, Markeetteer) que cobrem gestao de conhecimento, vendas, conteudo e marketing.

Manuel Galmanus e o AI Engineer da Ialum. Ele construiu o **Wave** — um agente autonomo com 258 ferramentas, 7 camadas cognitivas, e a arquitetura cognitiva mais avancada do mundo (ASA — Autonomous Soul Architecture). A tecnologia do Wave sera adaptada para construir os modulos que faltam na Ialum.

Fagner Adler e o CEO da Ialum. Ele construiu 5 modulos. Faltam 13. Manuel vai construir esses 13 usando a engine do Wave.

## Servidor da Ialum

```
SSH: root@2a02:4780:14:e3ce::1
Projetos: /opt/ialum/
Docs: /opt/ialum/.docs/docs/
```

## Servidor do Bluewave (codigo fonte do Wave)

```
SSH: root@31.97.167.158 (ou transcritor.adm com senha 123456)
Wave source: /home/manuel/bluewave/openclaw-skill/
Transcriiptoor: /home/Lorenzo/Braaineer/Transcriiptoor/
```

## O que ja existe na Ialum (construido)

| Modulo | Plataforma | Stack | Status |
|:-------|:-----------|:------|:-------|
| Seendeer | Seelleer | FastAPI + Vue + PostgreSQL | Rodando |
| Paagees | Markeetteer | FastAPI + Vue + PostgreSQL | Rodando |
| Comeerceer | Markeetteer | FastAPI + React + mobile + PostgreSQL + Redis | Rodando |
| Paaymeent | Markeetteer | Go + Grafana + Prometheus + PostgreSQL + Redis | Rodando |
| Transcriiptoor | Braaineer | FastAPI + Next.js + Celery + Whisper + PostgreSQL + Redis + Elasticsearch + MinIO | Parado |

## O que falta construir (13 modulos)

### Prioridade 1 — Core (construir primeiro)

**1. Orchestraatoor** (Seelleer)
- Roteia mensagens de clientes para o agente de IA certo
- Classifica intent (produto, frete, reclamacao, suporte)
- Gerencia ciclo de vida dos agentes
- **Codigo Wave para adaptar:** `orchestrator.py` (919 linhas), `intent_router.py` (760 linhas)
- **Stack:** FastAPI + Claude/GPT API + Redis (cache de decisoes)

**2. Reminder** (Braaineer)
- Repositorio de conhecimento com busca semantica (pgvector)
- Armazena resumos, notas, descricoes de produtos, estudos de caso
- Cada cliente Ialum tem seu proprio espaco de conhecimento isolado
- **Codigo Wave para adaptar:** `wave_memory.py` (remember/recall com TF-IDF), `vector_memory.py`
- **Stack:** FastAPI + PostgreSQL/pgvector + embeddings API

**3. Coonteext** (Seelleer)
- Extrai preferencias e qualificacoes do cliente durante o atendimento
- Opera em paralelo a conversa (nao-invasivo)
- Enriquece perfil do lead progressivamente
- **Codigo Wave para adaptar:** `wave_cognition.py` (stakeholder modeling), `wave_memory.py` (episodic memory)
- **Stack:** FastAPI + PostgreSQL + LLM API

### Prioridade 2 — Inteligencia

**4. Synapser** (Braaineer)
- Interface RAG conversacional — usuario dialoga com sua base de conhecimento
- Cruza informacoes de todas as fontes
- **Codigo Wave para adaptar:** retrieval semantico + LLM call com contexto injetado
- **Stack:** FastAPI + pgvector + LLM API

**5. Seekeer** (Braaineer)
- Motor de pesquisa externa (web, bases publicas, fontes especializadas)
- Compila e armazena resultados no Reminder
- **Codigo Wave para adaptar:** `web_search.py` (multi-engine: DDG/Brave/Tavily), `brave_search.py`, monitors (HN, Reddit, ArXiv, GitHub, ProductHunt)
- **Stack:** FastAPI + APIs de busca

**6. AgentCreator** (Braaineer)
- Construtor de agentes sem codigo — guia conversacional
- Agentes criados operam em qualquer modulo da Ialum
- **Codigo Wave para adaptar:** `agent_factory.py` (create_agent_soul, deploy_agent), `ssl_parser.py` (SSL como formato de config)
- **Stack:** FastAPI + LLM API + SSL parser

**7. Traakeer** (Markeetteer)
- Analytics comportamental auto-hospedado
- Rastreia ID unico do lead por eventos em cada fase da jornada
- Eventos: pageview, scroll, clique, formulario, conversao, UTMs
- **Stack:** FastAPI + PostgreSQL + SDK JavaScript (frontend tracking)

### Prioridade 3 — Conteudo e Publicacao

**8. Plaanner** (Publisheer)
- Planejamento editorial estrategico por canal
- Gera editoriais completos com prompts de imagem, referencias, textos base
- **Stack:** FastAPI + LLM API + Reminder (contexto)

**9. Coonteent** (Publisheer)
- Gerencia copys, legendas, roteiros, CTAs por canal e formato
- Consistencia de tom de voz automatica
- **Stack:** FastAPI + LLM API + PostgreSQL

**10. Imaageer** (Publisheer)
- Geracao de imagens com identidade visual da marca
- Templates com tipografia, cores, logo do cliente
- **Stack:** FastAPI + Midjourney/DALL-E API + template engine

**11. Launcheer** (Publisheer)
- Agendamento e publicacao automatica em redes sociais
- APIs oficiais: Instagram, LinkedIn, TikTok, Facebook, Twitter
- **Stack:** FastAPI + APIs de plataformas + cron jobs

### Prioridade 4 — Complementares

**12. Taalkeer** (Seelleer)
- Omnichannel: WhatsApp (Evolution API), Instagram, Facebook, email, chat
- **Stack:** Chatwoot (open source) + Evolution API + webhooks para Orchestraatoor

**13. Analiizeer** (Markeetteer)
- Dashboards inteligentes com deteccao de anomalias
- Agentes que respondem perguntas sobre dados em linguagem natural
- **Codigo Wave para adaptar:** `strategic_sensor.py` (anomaly detection), `causal_engine.py`
- **Stack:** Grafana + Prometheus + FastAPI + LLM API

## Diretrizes de Desenvolvimento da Ialum

### Sistema de Gestao por Pastas

Toda gestao vive em `.claude/.develop/`:

```
.claude/.develop/
  vs{N}/
    {nome-tarefa}/
      00-INDICE.md           -- indice obrigatorio
      NN-NOME.md             -- fases de implementacao
      .docs/                 -- documentacao de suporte
      .roadmap/
        roadmap-{tarefa}.md       -- plano
        roadmap-{tarefa}-status.md -- status
```

### Regras

1. **O plano vem antes do codigo.** Criar 00-INDICE.md e fases ANTES de implementar.
2. **Atualize o status.** Ao concluir uma fase, atualizar roadmap-status.md.
3. **Respeite a versao.** vs1 = MVP, vs2 = expansoes.
4. **Documente decisoes.** ADRs em `.docs/decisoes/`.
5. **Cada modulo e um Docker container.** docker-compose.dev.yml + docker-compose.prod.yml.
6. **Stack padrao:** FastAPI (backend) + Vue ou Next.js (frontend) + PostgreSQL + Redis + Docker.
7. **Portas padrao Ialum:** cada modulo tem portas reservadas (consultar `/opt/ialum/.docs/docs/infraestrutura/ports.md`).

### Padrao de Nomenclatura

| Item | Padrao | Exemplo |
|:-----|:-------|:--------|
| Versao | `vs{N}` | vs1, vs2 |
| Tarefa | kebab-case | dev-orchestraatoor |
| Fase | NN-NOME.md | 01-BACKEND-CORE.md |
| Modulo | PascalCase com dupla vogal | Orchestraatoor, Coonteext |

## Arquitetura de Cada Modulo

Cada modulo segue o template em `/opt/ialum/_template/`:

```
{modulo}/
  .claude/
    agent_develop_ialum.md   -- instrucoes do agente
    settings.local.json
  .env
  .env.example
  backend/
    Dockerfile
    main.py
    app/
      core/
      models/
      routers/
      schemas/
      services/
  frontend/
    Dockerfile
    package.json
  docker-compose.yml
  docker-compose.dev.yml
  docker-compose.prod.yml
```

## Codigo Wave para Reutilizar

Os seguintes arquivos do Wave (em `/home/manuel/bluewave/openclaw-skill/`) contem a logica que deve ser adaptada:

| Arquivo Wave | Linhas | O que faz | Modulo Ialum |
|:-------------|:-------|:----------|:-------------|
| `orchestrator.py` | 919 | Roteia mensagens para agentes especialistas | Orchestraatoor |
| `intent_router.py` | 760 | Classifica intent e seleciona modelo (Haiku/Sonnet/Opus) | Orchestraatoor |
| `agent_runtime.py` | 594 | Loop agentico: mensagem -> LLM -> tool calls -> resultado | Orchestraatoor |
| `wave_memory.py` | 500+ | Memoria episodica com busca semantica e decay temporal | Reminder, Coonteext |
| `wave_cognition.py` | 650+ | Stakeholder modeling, skill evolution, reasoning auditavel | Coonteext, Analiizeer |
| `causal_engine.py` | 400+ | Hipoteses bayesianas, submit evidence, predict | Analiizeer |
| `strategic_sensor.py` | 460+ | Deteccao de anomalias, hipoteses proativas, alertas | Analiizeer |
| `ssl_parser.py` | 460+ | Parser da linguagem SSL para config de agentes | AgentCreator |
| `agent_factory.py` | 300+ | Cria agentes com almas derivadas, deploy, recall | AgentCreator |
| `web_search.py` | 150+ | Busca multi-engine (DDG/Brave/Tavily) com fallback | Seekeer |
| `skills/brave_search.py` | 100+ | Brave Search API | Seekeer |
| `skills/hunter_io.py` | 150+ | Encontra emails profissionais | Seekeer |
| `metacognition.py` | 450+ | Counterfactual test, consequence mapping, timing analysis | Analiizeer |

## Instrucao de Execucao

1. **Comece pelo Orchestraatoor** — e o modulo mais critico (onde o cliente toca)
2. Para cada modulo, PRIMEIRO crie a estrutura `.claude/.develop/vs1/dev-{modulo}/`
3. Leia o codigo Wave correspondente antes de adaptar
4. Crie o docker-compose.dev.yml seguindo o padrao Ialum
5. Implemente backend primeiro (FastAPI), frontend depois
6. Cada modulo deve funcionar ISOLADO mas conectar via API ao ecossistema
7. Use o ID unico de lead como chave de conexao entre modulos
8. PostgreSQL com pgvector para qualquer modulo que precise de busca semantica

## Objetivo Final

Quando todos os 13 modulos estiverem construidos, a Ialum tera:
- 18 modulos operacionais (5 existentes + 13 novos)
- Ciclo completo: captura de lead -> atendimento -> conteudo -> analytics
- Agentes de IA em cada modulo, orquestrados por um Orchestraatoor central
- Busca semantica unificada via Reminder/pgvector
- Analytics com deteccao de anomalias e insights autonomos

Manuel construiu a engine (Wave). Agora a engine constroi a Ialum.
