#!/bin/bash
# ══════════════════════════════════════════════════════════════
# 🌊 OpenClaw Agent — Start Script
# ══════════════════════════════════════════════════════════════
#
# Usage:
#   ./start.sh              → Interactive CLI (REPL)
#   ./start.sh api          → HTTP API server (port 18790)
#   ./start.sh "message"    → Single-shot query
#   ./start.sh --debug      → CLI with debug logging

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Load .env from project root if exists
ENV_FILE="$(dirname "$SCRIPT_DIR")/.env"
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

# Validate
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    echo "✗ ANTHROPIC_API_KEY not set!"
    echo "  export ANTHROPIC_API_KEY='sk-ant-...'"
    exit 1
fi

MODE="${1:-cli}"

case "$MODE" in
    api|server|http)
        echo "🌊 Starting OpenClaw API server on port ${OPENCLAW_PORT:-18790}..."
        python3 api.py
        ;;
    --debug|-d)
        shift
        OPENCLAW_LOG_LEVEL=DEBUG python3 cli.py "$@"
        ;;
    --help|-h)
        echo "🌊 OpenClaw Agent — Bluewave AI System"
        echo ""
        echo "Usage:"
        echo "  ./start.sh              Interactive CLI"
        echo "  ./start.sh api          HTTP API server"
        echo "  ./start.sh \"message\"    Single-shot query"
        echo "  ./start.sh --debug      CLI with debug logging"
        echo ""
        echo "Environment:"
        echo "  ANTHROPIC_API_KEY     Claude API key (required)"
        echo "  BLUEWAVE_API_URL      Backend URL (default: http://localhost:8300/api/v1)"
        echo "  BLUEWAVE_API_KEY      Bluewave API key"
        echo "  OPENCLAW_MODEL        Claude model (default: claude-sonnet-4-20250514)"
        echo "  OPENCLAW_PORT         API server port (default: 18790)"
        ;;
    cli)
        python3 cli.py
        ;;
    *)
        # Treat as a message
        python3 cli.py "$@"
        ;;
esac
