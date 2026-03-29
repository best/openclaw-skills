#!/bin/bash
# Archive a Discord thread via Discord REST API
# Usage: ./archive-thread.sh <thread_id>
# Requires: DISCORD_BOT_TOKEN env var, or reads from OpenClaw config

set -euo pipefail

THREAD_ID="${1:-}"

if [ -z "$THREAD_ID" ]; then
    echo '{"ok":false,"error":"Thread ID is required"}' >&2
    exit 1
fi

# Resolve bot token: env var first, then OpenClaw config
if [ -z "${DISCORD_BOT_TOKEN:-}" ]; then
    CONFIG_FILE="${OPENCLAW_CONFIG:-/root/.openclaw/openclaw.json}"
    if [ -f "$CONFIG_FILE" ]; then
        DISCORD_BOT_TOKEN=$(python3 -c "
import json, sys
try:
    c = json.load(open('$CONFIG_FILE'))
    print(c['channels']['discord']['token'])
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null) || true
    fi
fi

if [ -z "${DISCORD_BOT_TOKEN:-}" ]; then
    echo '{"ok":false,"error":"No Discord bot token found"}' >&2
    exit 1
fi

# Call Discord API to archive the thread
HTTP_CODE=$(curl -s -o /tmp/archive-response.json -w "%{http_code}" \
    -X PATCH "https://discord.com/api/v10/channels/${THREAD_ID}" \
    -H "Authorization: Bot ${DISCORD_BOT_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"archived": true}')

sleep 0.5  # Rate limit courtesy

if [ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 300 ]; then
    ARCHIVED=$(python3 -c "import json; d=json.load(open('/tmp/archive-response.json')); print('true' if d.get('thread_metadata',{}).get('archived') else 'false')" 2>/dev/null || echo "unknown")
    echo "{\"ok\":true,\"threadId\":\"${THREAD_ID}\",\"archived\":${ARCHIVED},\"httpCode\":${HTTP_CODE}}"
else
    ERROR=$(cat /tmp/archive-response.json 2>/dev/null || echo "unknown")
    echo "{\"ok\":false,\"threadId\":\"${THREAD_ID}\",\"httpCode\":${HTTP_CODE},\"error\":$(python3 -c "import json; print(json.dumps('$ERROR'))" 2>/dev/null || echo "\"$ERROR\"")}" >&2
    exit 1
fi