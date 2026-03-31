IALUM PROJECT MAP — FULL TECHNICAL OVERVIEW (Generated 2026-03-25)

═══════════════════════════════════════════════════════════════
1. ACTIVE PROJECTS ON THIS SERVER
═══════════════════════════════════════════════════════════════

PROJECT: BLUEWAVE
  Location: /home/manuel/bluewave/
  Stack: FastAPI + React + 47 skill modules + Hedera blockchain
  Status: Production (680+ autonomous cycles)
  Git: 115+ commits
  Key dirs:
    backend/app/routers/     — 26 API endpoints
    backend/app/services/    — 23 business logic services
    backend/app/models/      — 20 SQLAlchemy models
    frontend/src/pages/      — 18 React pages
    openclaw-skill/          — Wave autonomous engine (158 tools)
    openclaw-skill/skills/   — 47 Python skill modules
    openclaw-skill/prompts/  — Soul (ASA), cognitive protocol
    agents/                  — Child agents (sentinel, revenue_hunter)
    docs/whitepapers/        — ASA, PUT, SSL, math foundations

PROJECT: TRANSCRIIPTOOR (= Braainner.Transcriptor)
  Location: /home/Lorenzo/Braaineer/Transcriiptoor/
  Stack: FastAPI + Next.js 16 + Celery + faster-whisper + PostgreSQL + Redis + MinIO + Elasticsearch
  Status: MVP 61% complete (5.5/9 phases done)
  Owner: Lorenzo (Ialum team)

  Directory structure:
    backend/app/routers/     — 15 API endpoints (auth, transcriptions, upload, url, search, projects, notes, documents, meetings, ws, admin)
    backend/app/services/    — 12 services
    backend/app/models/      — 10 models (user, transcription, segment, participant, project, document, note, meeting, api_key)
    worker/app/engines/      — faster-whisper STT engine
    worker/app/tasks/        — Celery tasks (download, preprocess, transcribe, postprocess)
    worker/app/diarization/  — pyannote speaker ID
    frontend/app/            — Next.js App Router pages
    frontend/components/     — React components (transcricoes, upload, meetings, ui)
    frontend/hooks/          — Custom hooks (useAuth, useTranscricoes, useUpload, useSearch, etc.)
    meeting-bot/             — Google Meet bot (Playwright)
    .claude/.develop/vs1/    — Development phases & docs

  API Endpoints:
    POST /auth/register, /auth/login, /auth/refresh
    POST /upload/presign, /upload/confirm
    POST /url/preview, /transcriptions/from-url
    GET/PATCH/DELETE /transcriptions, /transcriptions/:id
    GET /transcriptions/:id/segments
    GET /search?q=...&speaker=...&tag=...
    CRUD /projects, /transcriptions/:id/notes, /transcriptions/:id/documents
    POST /meetings/:id/start, /meetings/:id/stop
    WS /v1/ws/transcriptions/:id/status
    WS /v1/ws/dashboard

  Transcription pipeline:
    Upload/URL → yt-dlp download → FFmpeg convert WAV 16kHz mono → chunk (30min) → faster-whisper → merge segments → diarization (optional, pyannote) → spelling correction (optional, Claude Haiku) → save PostgreSQL → index Elasticsearch

  Docker services:
    postgres:5432, redis:6379, minio:9000, elasticsearch:9200, backend:8100, worker, meeting-bot, frontend:3100

  Phase status:
    ✅ 01 Backend Core (API, DB, auth, upload, storage, Celery)
    ✅ 02 Transcription Engine (Whisper, diarization, spelling)
    ✅ 03 Frontend Base (dashboard, upload, editor, search)
    ✅ 04 WebSocket Real-Time (progress via Redis Pub/Sub)
    🟡 05 URL Transcription (yt-dlp works, YouTube blocked by bot detection)
    ✅ 06 Search Indexing (Elasticsearch with Brazilian analyzer)
    ❌ 07 Documentation & Organization (tags, categories, folders, notes, export)
    ❌ 08 Meeting Bot (Google Meet bot, multi-meeting)
    ❌ 09 AI Agents (customizable agents, workflows, LLM)

  Known blockers:
    - YouTube URL transcription: blocked by bot detection (needs cookies.txt)
    - Diarization disabled by default (needs HF_TOKEN)
    - ANTHROPIC_API_KEY empty in .env (spelling correction won't work)

  Config (.env):
    POSTGRES_DB=transcriiptoor
    WHISPER_MODEL=base, WHISPER_DEVICE=cpu, WHISPER_COMPUTE_TYPE=int8
    CORRECTION_MODEL=claude-haiku-4-5-20251001
    GOOGLE_BOT_EMAIL=ialumbot@gmail.com
    ENABLE_DIARIZATION=false
    ENABLE_SPELLING_CORRECTION=true (but no API key)

  Dev docs:
    .claude/.develop/vs1/dev-mvp/.docs/visao-geral/01-VISAO-GERAL.md
    .claude/.develop/vs1/dev-mvp/.docs/visao-geral/02-ARQUITETURA.md
    .claude/.develop/vs1/dev-mvp/.docs/visao-geral/05-API.md
    .claude/.develop/vs1/dev-mvp/.roadmap/roadmap-dev-start-status.md

═══════════════════════════════════════════════════════════════
2. IALUM PLATFORM ARCHITECTURE (4 Platforms)
═══════════════════════════════════════════════════════════════

BRAAINNER (Knowledge Layer) — PARTIALLY IMPLEMENTED
  Modules: Transcriptor (= Transcriiptoor ✅), Reminder (pgvector, ❌), Seekeer (❌), Synapser (RAG, ❌), Agent Creator (❌)
  Data flow: Raw data → Transcriptor → Reminder (compiled) → Agents

SEELLEER (Sales Layer) — CONCEPTUAL
  Modules: Taalkeer (omnichannel WhatsApp/IG/email), Orchestraatoor (LLM router), Coonteext (lead enrichment), Seendeer (freight)
  Key: Paaneels sub-module for real-time quotation + automatic frete

PUBLISHEER (Content Layer) — CONCEPTUAL
  Modules: Plaanner (editorial), Coonteent (copy), Imaageer (visuals), Launcheer (scheduling+publishing)

MARKEETTEER (Analytics Layer) — CONCEPTUAL
  Modules: Paagees (landing pages), Traakeer (first-party analytics), Analiizeer (dashboards), Ecommerceer

CROSS-PLATFORM:
  - Unified lead ID across all platforms (first touch → post-sale)
  - VPS per client (LGPD compliance)
  - All modules share PostgreSQL + message queues

═══════════════════════════════════════════════════════════════
3. TECH STACK SUMMARY
═══════════════════════════════════════════════════════════════

Backend:    FastAPI, SQLAlchemy 2.0 (async), Alembic, Celery, Redis, PostgreSQL 16
Frontend:   React 18-19, TypeScript, Next.js 16, Vite, Tailwind CSS, Radix UI, Zustand, React Query
AI/ML:      Claude (Haiku/Sonnet/Opus), faster-whisper, pyannote, pgvector
Infra:      Docker Compose, MinIO, Elasticsearch 8.13, Nginx
Blockchain: Hedera (HBAR, HCS, HTS), Starknet (Cairo/MIDAS)
Payments:   Mercado Pago (Brazil), Stripe (international), HBAR micropayments
Integrations: yt-dlp, Playwright, Google Meet API, Evolution API (WhatsApp), X/Twitter API
