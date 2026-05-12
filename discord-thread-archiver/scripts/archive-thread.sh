#!/bin/bash
# Archive a Discord thread via Discord REST API
# Usage: ./archive-thread.sh [--dry-run] <thread_id>
# Requires: DISCORD_BOT_TOKEN env var, or reads from OpenClaw config

set -euo pipefail

DRY_RUN=false
if [ "${1:-}" = "--dry-run" ]; then
    DRY_RUN=true
    shift
fi

THREAD_ID="${1:-}"

if [ -z "$THREAD_ID" ]; then
    echo '{"ok":false,"error":"Thread ID is required"}' >&2
    exit 1
fi

if [ "$DRY_RUN" = true ]; then
    printf '{"ok":true,"dryRun":true,"threadId":"%s","archived":false}\n' "$THREAD_ID"
    exit 0
fi

# Resolve bot token: env var first, then OpenClaw config
if [ -z "${DISCORD_BOT_TOKEN:-}" ]; then
    CONFIG_FILE="${OPENCLAW_CONFIG:-/root/.openclaw/openclaw.json}"
    if [ -f "$CONFIG_FILE" ]; then
        DISCORD_BOT_TOKEN=$(CONFIG_FILE="$CONFIG_FILE" python3 - <<'PY' 2>/dev/null || true
import json, os, sys
try:
    c = json.load(open(os.environ['CONFIG_FILE']))
    print(c['channels']['discord']['token'])
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
PY
)
    fi
fi

if [ -z "${DISCORD_BOT_TOKEN:-}" ]; then
    echo '{"ok":false,"error":"No Discord bot token found"}' >&2
    exit 1
fi

# Call Discord API to archive the thread
RESPONSE_FILE="/tmp/archive-thread-${THREAD_ID}-response.json"
HTTP_CODE=$(curl -s -o "$RESPONSE_FILE" -w "%{http_code}" \
    -X PATCH "https://discord.com/api/v10/channels/${THREAD_ID}" \
    -H "Authorization: Bot ${DISCORD_BOT_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"archived": true}')

sleep 0.5  # Rate limit courtesy

if [ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 300 ]; then
    ARCHIVED=$(RESPONSE_FILE="$RESPONSE_FILE" python3 - <<'PY' 2>/dev/null || echo "unknown"
import json, os
d = json.load(open(os.environ['RESPONSE_FILE']))
print('true' if d.get('thread_metadata', {}).get('archived') else 'false')
PY
)
    printf '{"ok":true,"threadId":"%s","archived":%s,"httpCode":%s}\n' "$THREAD_ID" "$ARCHIVED" "$HTTP_CODE"
else
    ERROR_JSON=$(RESPONSE_FILE="$RESPONSE_FILE" python3 - <<'PY' 2>/dev/null || echo '"unknown"'
import json, os
try:
    raw = open(os.environ['RESPONSE_FILE']).read()
except FileNotFoundError:
    raw = 'unknown'
print(json.dumps(raw))
PY
)
    printf '{"ok":false,"threadId":"%s","httpCode":%s,"error":%s}\n' "$THREAD_ID" "$HTTP_CODE" "$ERROR_JSON" >&2
    exit 1
fi
