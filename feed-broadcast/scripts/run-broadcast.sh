#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK="${FEED_BROADCAST_TASK:-/tmp/feed-broadcast-task.json}"
DECISION="${FEED_BROADCAST_DECISION:-/tmp/feed-broadcast-decision.json}"
OUT="$(python3 "$SCRIPT_DIR/feed_broadcast_ctl.py" --repo "${FEED_REPO:?FEED_REPO is required}" --state "${FEED_BROADCAST_STATE:?FEED_BROADCAST_STATE is required}" --target "${FEED_BROADCAST_TARGET:?FEED_BROADCAST_TARGET is required}" --log-target "${FEED_BROADCAST_LOG_TARGET:-}" --task "$TASK" --decision "$DECISION" prepare)"
printf '%s
' "$OUT"
STATUS="$(printf '%s
' "$OUT" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status",""))')"
if [ "$STATUS" = "no_content" ]; then
  exit 0
fi
cat <<EOF
NEXT: read $TASK, write decision JSON to $DECISION, then run:
python3 "$SCRIPT_DIR/feed_broadcast_ctl.py" --repo "${FEED_REPO:?FEED_REPO is required}" --state "${FEED_BROADCAST_STATE:?FEED_BROADCAST_STATE is required}" --target "${FEED_BROADCAST_TARGET:?FEED_BROADCAST_TARGET is required}" --log-target "${FEED_BROADCAST_LOG_TARGET:-}" --task "$TASK" --decision "$DECISION" finalize
EOF
