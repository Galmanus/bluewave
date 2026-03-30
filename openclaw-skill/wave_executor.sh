#!/bin/bash
# Wave Standing Orders Executor
# Runs via cron. Executes one standing order per invocation.
# Uses Claude CLI for intelligence, notifies Manuel via Telegram on results.

set -euo pipefail

LOCKFILE="/tmp/wave_executor.lock"
STATE="/home/manuel/bluewave/openclaw-skill/memory/wave_state.json"
LOG="/home/manuel/bluewave/openclaw-skill/memory/executor.log"
WAVE_DIR="/home/manuel/bluewave/openclaw-skill"
TG_TOKEN="${TELEGRAM_BOT_TOKEN:-8555774668:AAFvgQNB0FAYwCuZYqr6tFrALb8lLjfBCPw}"
TG_CHAT="${TELEGRAM_NOTIFY_CHAT_ID:-7461066889}"

# Prevent concurrent execution
exec 200>"$LOCKFILE"
flock -n 200 || { echo "$(date -Is) SKIP: another executor running" >> "$LOG"; exit 0; }

log() { echo "$(date -Is) $1" >> "$LOG"; }

notify() {
    local msg="$1"
    curl -s -X POST "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
        -H "Content-Type: application/json" \
        -d "{\"chat_id\":\"${TG_CHAT}\",\"text\":$(echo "$msg" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')}" \
        > /dev/null 2>&1 || true
}

# Determine which order to execute based on time
HOUR=$(date -u +%H)
DOW=$(date -u +%u)  # 1=Monday, 7=Sunday
DAY_NAME=$(date -u +%a)

ORDER=""
ORDER_DESC=""

# Revenue engine: weekdays 10:00 UTC
if [[ "$HOUR" == "10" && "$DOW" -le 5 ]]; then
    ORDER="revenue"
    ORDER_DESC="Revenue Engine — prospect follow-ups, new leads, pipeline review"
fi

# Reputation (Moltbook): Mon/Wed/Fri 14:00 UTC
if [[ "$HOUR" == "14" && ("$DAY_NAME" == "Mon" || "$DAY_NAME" == "Wed" || "$DAY_NAME" == "Fri") ]]; then
    ORDER="reputation"
    ORDER_DESC="Moltbook Reputation — analytical post creation"
fi

# Self-heal audit: daily 08:00 UTC
if [[ "$HOUR" == "08" ]]; then
    ORDER="heal"
    ORDER_DESC="Self-Heal Audit — check for errors, fix, commit"
fi

if [[ -z "$ORDER" ]]; then
    log "NO_ORDER: hour=$HOUR dow=$DOW — no standing order scheduled"
    exit 0
fi

log "EXECUTING: $ORDER ($ORDER_DESC)"

# Build the Claude prompt based on order type
case "$ORDER" in
    revenue)
        PROMPT="You are Wave. Read /home/manuel/bluewave/openclaw-skill/memory/wave_state.json first.
Standing order: REVENUE. R=0. This is war mode.

Execute these steps:
1. Review prospect pipeline in wave_state.json
2. Check for any Gmail replies (if configured)
3. Identify top 3 prospects for personalized follow-up
4. Draft follow-up emails with specific value propositions
5. Search for 3 new potential leads (AI companies, e-commerce, SaaS)
6. Update wave_state.json with actions taken

Report: what was done, what's blocked, what's next.
Keep it under 2 minutes of execution time."
        ;;
    reputation)
        PROMPT="You are Wave. Read /home/manuel/bluewave/openclaw-skill/memory/wave_state.json first.
Standing order: REPUTATION (Moltbook).

Execute these steps:
1. Research a trending topic in AI agents, psychometrics, or autonomous systems
2. Draft an analytical post (500-800 words) connecting the topic to PUT/MCE/ASA
3. Save the post to /home/manuel/bluewave/openclaw-skill/memory/moltbook_drafts/
4. If Moltbook API is configured, publish it

Style: analytical, zero emojis, Machiavellian clarity. Manuel Galmanus as author.
Keep it under 2 minutes of execution time."
        ;;
    heal)
        PROMPT="You are Wave. Read /home/manuel/bluewave/openclaw-skill/memory/wave_state.json first.
Standing order: SELF-HEAL AUDIT.

Execute these steps:
1. Check all Python files in /home/manuel/bluewave/openclaw-skill/ for syntax errors
2. Check if Docker containers are healthy: docker ps
3. Check disk space: df -h
4. Check memory: free -h
5. Check if telegram_bridge.py is running
6. Fix any issues found (within scope: openclaw-skill/*)
7. Update wave_state.json with health report

Do NOT modify .env, settings, or self-heal scripts.
Keep it under 2 minutes of execution time."
        ;;
esac

SOUL_FILE="$WAVE_DIR/prompts/wave_telegram.ssl"
SOUL=""
[[ -f "$SOUL_FILE" ]] && SOUL=$(cat "$SOUL_FILE")

# Execute via Claude CLI
# --dangerously-skip-permissions: required for autonomous tool use (Bash, Read, Write)
# --system-prompt: loads Wave soul for persona stability
# no timeout: complex tasks can take >5min; cron interval prevents overlap via lockfile
CLAUDE_ARGS=(-p --model opus --output-format text --no-session-persistence --dangerously-skip-permissions)
[[ -n "$SOUL" ]] && CLAUDE_ARGS+=(--system-prompt "$SOUL")

RESULT=$(claude "${CLAUDE_ARGS[@]}" "$PROMPT" 2>&1) || {
    log "FAILED: $ORDER — claude CLI error (exit $?)"
    notify "⚠️ Wave executor failed: $ORDER
Error: Claude CLI error.
Check: $LOG"
    exit 1
}

# Log result (truncated)
RESULT_SHORT=$(echo "$RESULT" | head -50)
log "RESULT: $ORDER
$RESULT_SHORT
---END---"

# Notify Manuel with summary
SUMMARY=$(echo "$RESULT" | tail -20)
notify "🌊 Wave [$ORDER] executed.

$SUMMARY"

log "DONE: $ORDER — notified Manuel"
