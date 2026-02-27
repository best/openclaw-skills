#!/usr/bin/env bash
# List uploaded images from the local log
# Usage: list.sh [--recent N] [--search TERM]
set -euo pipefail

CHEVERETO_LOG="${CHEVERETO_LOG:-$HOME/.openclaw/workspace/memory/chevereto-uploads.jsonl}"

if [[ ! -f "$CHEVERETO_LOG" ]]; then
  echo "No uploads found (log file does not exist)"
  exit 0
fi

RECENT="${1:-}"
SEARCH="${2:-}"

if [[ "$RECENT" == "--recent" && -n "$SEARCH" ]]; then
  tail -n "$SEARCH" "$CHEVERETO_LOG" | jq -r '[.id, .title, .viewer_url, .uploaded_at] | @tsv' | grep -v DELETED
elif [[ "$RECENT" == "--search" && -n "$SEARCH" ]]; then
  grep -i "$SEARCH" "$CHEVERETO_LOG" | jq -r '[.id, .title, .viewer_url, .uploaded_at] | @tsv' | grep -v DELETED
else
  jq -r '[.id, .title, .viewer_url, .uploaded_at] | @tsv' "$CHEVERETO_LOG" | grep -v DELETED
fi
