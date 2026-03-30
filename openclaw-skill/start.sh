#!/bin/bash
set -e

# Wave Sovereign Startup — Gemini Edition

if [ -z "${GEMINI_API_KEY:-}" ]; then
    echo "✗ GEMINI_API_KEY not set!"
    exit 1
fi

echo "🌊 Wave (Gemini Engine) is rising..."
python3 api.py &
python3 telegram_bridge.py &
wait
