#!/usr/bin/env bash
# verify-dream.sh — Post-consolidation verification checks
# Exit 0 = all pass, exit 1 = has failures
# Output: one line per check, prefixed PASS/FAIL

set -euo pipefail

WS="${OPENCLAW_WORKSPACE:-/root/.openclaw/workspace}"
MEMORY="$WS/MEMORY.md"
FAILS=0

# 1. Line count
LINES=$(wc -l < "$MEMORY")
if (( LINES <= 300 )); then
  echo "PASS: MEMORY.md = ${LINES} lines (≤300)"
else
  echo "FAIL: MEMORY.md = ${LINES} lines (>300)"
  FAILS=$((FAILS+1))
fi

# 2. Stale relative dates (exclude structural descriptions in schema/layer definitions)
STALE_LINES=$(grep -nE '昨天|上周|最近|前几天|yesterday|last week|前天' "$MEMORY" 2>/dev/null \
  | grep -vE '近期层|T[0-3]|分层|架构|设计|记忆分层' || true)
STALE_COUNT=$(echo "$STALE_LINES" | grep -c . 2>/dev/null || echo "0")
if [[ "$STALE_COUNT" == "0" || -z "$STALE_LINES" ]]; then
  echo "PASS: No stale relative dates"
else
  echo "FAIL: Found ${STALE_COUNT} lines with relative dates"
  echo "$STALE_LINES" | head -5
  FAILS=$((FAILS+1))
fi

# 3. Reference index integrity — check that referenced files exist
MISSING=0
while IFS= read -r ref_path; do
  full="$WS/$ref_path"
  if [[ ! -f "$full" ]]; then
    echo "FAIL: Referenced file missing: $ref_path"
    MISSING=$((MISSING+1))
  fi
done < <(grep -oE 'memory/reference/[a-z0-9_-]+\.md' "$MEMORY" 2>/dev/null || true)

if (( MISSING == 0 )); then
  echo "PASS: All referenced files exist"
else
  FAILS=$((FAILS+MISSING))
fi

# 4. Index line width — entries over 150 chars
LONG=$(awk 'length > 150' "$MEMORY" | wc -l)
if (( LONG <= 5 )); then
  echo "PASS: Long lines (>150ch) = ${LONG} (≤5 tolerance)"
else
  echo "WARN: ${LONG} lines exceed 150 chars"
fi

# Summary
echo "---"
echo "Checks: $((4-FAILS>0 ? 4-FAILS : 0))/4 passed, ${FAILS} failed"
exit $FAILS
