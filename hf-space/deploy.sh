#!/bin/bash
set -euo pipefail

# ── Wave Hugging Face Space Deploy ────────────────────────────
#
# Deploys the Wave agent system to Hugging Face Spaces.
# Runs as a Docker container with the FastAPI server on port 7860.
#
# Prerequisites:
#   - Hugging Face account (huggingface.co)
#   - huggingface-cli installed: pip install huggingface_hub
#   - HF token with write access: huggingface-cli login
#
# Usage:
#   cd hf-space && bash deploy.sh
#
# After deploy, set secrets in HF Space settings:
#   - ANTHROPIC_API_KEY (required)
#   - HEDERA_OPERATOR_ID (optional)
#   - HEDERA_OPERATOR_KEY (optional)
#   - HEDERA_HCS_TOPIC_ID (optional)
#   - MOLTBOOK_API_KEY (optional)

SPACE_NAME="Galmanus/wave"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HF_DIR="$(dirname "$0")"
STAGING_DIR="/tmp/hf-wave-deploy"

echo "=== Wave → Hugging Face Space Deploy ==="
echo "Space: $SPACE_NAME"
echo ""

# Check huggingface-cli
if ! command -v huggingface-cli &>/dev/null; then
    echo "Installing huggingface_hub..."
    pip install huggingface_hub
fi

# Create or clone the Space repo
if [ -d "$STAGING_DIR" ]; then
    echo "Cleaning previous staging..."
    rm -rf "$STAGING_DIR"
fi

echo "[1/5] Creating Space repository..."
huggingface-cli repo create "$SPACE_NAME" --type space --space-sdk docker 2>/dev/null || true
git clone "https://huggingface.co/spaces/$SPACE_NAME" "$STAGING_DIR" 2>/dev/null || {
    mkdir -p "$STAGING_DIR"
    cd "$STAGING_DIR"
    git init
    git remote add origin "https://huggingface.co/spaces/$SPACE_NAME"
}

echo "[2/5] Copying files..."
# Copy HF Space config
cp "$HF_DIR/Dockerfile" "$STAGING_DIR/"
cp "$HF_DIR/requirements.txt" "$STAGING_DIR/"
cp "$HF_DIR/README.md" "$STAGING_DIR/"

# Copy the agent system
mkdir -p "$STAGING_DIR/openclaw-skill"
rsync -av --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' \
    "$REPO_ROOT/openclaw-skill/" "$STAGING_DIR/openclaw-skill/"

# Ensure memory directory exists but is empty (fresh start)
mkdir -p "$STAGING_DIR/openclaw-skill/memory"
touch "$STAGING_DIR/openclaw-skill/memory/.gitkeep"

echo "[3/5] Staging files..."
cd "$STAGING_DIR"
git add -A

echo "[4/5] Committing..."
git commit -m "Wave deploy: 158 tools, 10 agents, ASA + PUT" 2>/dev/null || echo "No changes to commit"

echo "[5/5] Pushing to Hugging Face..."
git push origin main 2>/dev/null || git push origin master 2>/dev/null || {
    echo ""
    echo "Push failed. You may need to login first:"
    echo "  huggingface-cli login"
    echo ""
    echo "Then run this script again."
    exit 1
}

echo ""
echo "=== Deploy Complete ==="
echo "Space URL: https://huggingface.co/spaces/$SPACE_NAME"
echo ""
echo "IMPORTANT: Set these secrets in Space settings:"
echo "  https://huggingface.co/spaces/$SPACE_NAME/settings"
echo ""
echo "  ANTHROPIC_API_KEY=sk-ant-..."
echo "  HEDERA_OPERATOR_ID=0.0.xxxxx (optional)"
echo "  HEDERA_OPERATOR_KEY=302e... (optional)"
echo "  HEDERA_HCS_TOPIC_ID=0.0.xxxxx (optional)"
echo "  MOLTBOOK_API_KEY=... (optional)"
echo ""
echo "The Space will build and start automatically after push."
echo "Wave will be available at: https://$SPACE_NAME.hf.space"
