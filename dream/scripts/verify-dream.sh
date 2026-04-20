#!/usr/bin/env bash
# verify-dream.sh — Post-consolidation verification checks
# Exit 0 = all pass, exit 1 = has failures

set -euo pipefail

WS="${OPENCLAW_WORKSPACE:-/root/.openclaw/workspace}"
MEMORY="$WS/MEMORY.md"
FAILS=0

# 1. Line count budget
LINES=$(wc -l < "$MEMORY")
if (( LINES <= 300 )); then
  echo "PASS: MEMORY.md = ${LINES} lines (≤300)"
else
  echo "FAIL: MEMORY.md = ${LINES} lines (>300)"
  FAILS=$((FAILS+1))
fi

# 2. No stale relative dates in content (exclude structural descriptions)
STALE_COUNT=$(grep -cE '昨天|上周|最近|前几天|yesterday|last week|前天' "$MEMORY" 2>/dev/null || echo "0")
# Subtract lines that are architectural descriptions containing these words legitimately
ARCH_LINES=$(grep -nE '昨天|上周|最近|前几天' "$MEMORY" 2>/dev/null | grep -cE '近期层|T[0-3]|分层|注入层|归档层|知识层' || echo "0")
ADJUSTED=$((STALE_COUNT - ARCH_LINES))
if (( ADJUSTED <= 0 )); then
  echo "PASS: No stale relative dates"
else
  echo "FAIL: Found ${ADJUSTED} lines with stale relative dates"
  FAILS=$((FAILS+1))
fi

# 3. Long index entries (>150 chars) — tolerance 5
LONG=$(awk 'length > 150' "$MEMORY" | wc -l)
if (( LONG <= 5 )); then
  echo "PASS: Long lines (>150ch) = ${LONG} (≤5 tolerance)"
else
  echo "WARN: ${LONG} lines exceed 150 chars"
fi

# 4. Wiki vault accessible
if wiki_status >/dev/null 2>&1; then
  echo "PASS: Wiki vault reachable"
else
  echo "WARN: Wiki vault not reachable"
fi

# Summary
echo "---"
echo "Checks: $((4-FAILS>0 ? 4-FAILS : 0))/4 passed, ${FAILS} failed"
exit $FAILS
