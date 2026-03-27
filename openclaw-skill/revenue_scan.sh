#!/bin/bash
# REVENUE SCANNER — Aggregates market signals, identifies monetization opportunities
# Usage: ./revenue_scan.sh [focus]  (default: ai_tools)

cd /home/manuel/bluewave/openclaw-skill
FOCUS="${1:-ai_tools}"
OUT="/tmp/revenue_scan_$(date +%Y%m%d_%H%M).md"

echo "============================================================"
echo "  REVENUE OPPORTUNITY SCANNER"
echo "  Focus: $FOCUS | Date: $(date '+%Y-%m-%d %H:%M')"
echo "============================================================"
echo ""

echo "# Revenue Scan — $(date '+%Y-%m-%d %H:%M') — Focus: $FOCUS" > "$OUT"
echo "" >> "$OUT"

# Parallel signal gathering
echo "[1/4] Scanning Hacker News..."
HN=$(python3 skill_executor.py hn_top '{}' 2>/dev/null | head -80)
echo "[2/4] Scanning Product Hunt..."
PH=$(python3 skill_executor.py ph_today '{}' 2>/dev/null | head -80)
echo "[3/4] Scanning GitHub Trending..."
GH=$(python3 skill_executor.py gh_trending_repos '{}' 2>/dev/null | head -80)
echo "[4/4] Scanning HuggingFace..."
HF=$(python3 skill_executor.py hf_trending '{"category": "text-generation"}' 2>/dev/null | head -80)

echo ""
echo "## RAW SIGNALS" >> "$OUT"

echo "### Hacker News" >> "$OUT"
echo '```' >> "$OUT"
echo "$HN" >> "$OUT"
echo '```' >> "$OUT"

echo "### Product Hunt" >> "$OUT"
echo '```' >> "$OUT"
echo "$PH" >> "$OUT"
echo '```' >> "$OUT"

echo "### GitHub Trending" >> "$OUT"
echo '```' >> "$OUT"
echo "$GH" >> "$OUT"
echo '```' >> "$OUT"

echo "### HuggingFace" >> "$OUT"
echo '```' >> "$OUT"
echo "$HF" >> "$OUT"
echo '```' >> "$OUT"

echo "" >> "$OUT"
echo "## ANALYSIS FRAMEWORK" >> "$OUT"
cat >> "$OUT" << 'ANALYSIS'

For each opportunity found in the signals above, evaluate:

| # | Opportunity | Why Now | Pricing Model | Hours to MVP | $/week | First Step | Score |
|---|-------------|---------|---------------|-------------|--------|------------|-------|
| 1 |             |         |               |             |        |            |  /10  |
| 2 |             |         |               |             |        |            |  /10  |
| 3 |             |         |               |             |        |            |  /10  |
| 4 |             |         |               |             |        |            |  /10  |
| 5 |             |         |               |             |        |            |  /10  |

Scoring: signal_strength(1-3) × feasibility(1-3) × revenue_potential(1-3) = /10 normalized

RULES:
- MVP must be buildable in <40 hours
- Must generate revenue within 2 weeks of launch
- No "build a platform" — think tools, APIs, templates, services
- Prefer recurring revenue over one-time
ANALYSIS

echo "Signals collected. Report: $OUT"
echo ""
cat "$OUT"
