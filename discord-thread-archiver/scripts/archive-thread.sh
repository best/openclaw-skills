#!/usr/bin/env bash
# Archive a Discord thread by ID.
# Usage: archive-thread.sh <thread_id>
# Exit code 0 = success, 1 = error. Prints HTTP status code.
set -euo pipefail

THREAD_ID="${1:?Usage: archive-thread.sh <thread_id>}"
BOT_TOKEN=$(python3 -c "import json; print(json.load(open('/root/.openclaw/openclaw.json'))['channels']['discord']['token'])")

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH \
  -H "Authorization: Bot $BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -H "User-Agent: DiscordBot (https://openclaw.ai, 1.0)" \
  -d '{"archived": true}' \
  "https://discord.com/api/v10/channels/${THREAD_ID}")

echo "$HTTP_CODE"
[[ "$HTTP_CODE" == 2* ]] && exit 0 || exit 1
