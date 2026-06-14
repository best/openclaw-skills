#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK="${FEED_SCORE_TASK:-/tmp/feed-score-task.json}"
OUT="$(python3 "$SCRIPT_DIR/feed_score_ctl.py" --repo "${FEED_REPO:?FEED_REPO is required}" --task "$TASK" prepare)"
printf '%s
' "$OUT"
STATUS="$(printf '%s
' "$OUT" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status",""))')"
case "$STATUS" in
  no_content)
    exit 0
    ;;
  needs_cleanup|needs_finalize)
    python3 "$SCRIPT_DIR/feed_score_ctl.py" --repo "${FEED_REPO:?FEED_REPO is required}" --task "$TASK" finalize --push
    exit 0
    ;;
  needs_scoring)
    cat <<EOF
NEXT: read $TASK, write scored results JSON to the task scoredResultsPath, then run:
python3 "$SCRIPT_DIR/feed_score_ctl.py" --repo "${FEED_REPO:?FEED_REPO is required}" --task "$TASK" finalize --push
EOF
    ;;
  *)
    echo "FAILED: unexpected prepare status=$STATUS" >&2
    exit 2
    ;;
esac
