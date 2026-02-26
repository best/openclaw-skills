#!/usr/bin/env bash
# List uploaded images from the local log
# Usage: list.sh [--recent N] [--search TERM]
set -euo pipefail

IMGLAB_LOG="${IMGLAB_LOG:-$HOME/.openclaw/workspace/memory/imglab-uploads.jsonl}"

if [[ ! -f "$IMGLAB_LOG" ]]; then
  echo "No uploads found (log file does not exist)"
  exit 0
fi

RECENT="${1:-}"
SEARCH="${2:-}"

if [[ "$RECENT" == "--recent" && -n "$SEARCH" ]]; then
  tail -n "$SEARCH" "$IMGLAB_LOG" | jq -r '[.id, .title, .viewer_url, .uploaded_at] | @tsv' | grep -v DELETED
elif [[ "$RECENT" == "--search" && -n "$SEARCH" ]]; then
  grep -i "$SEARCH" "$IMGLAB_LOG" | jq -r '[.id, .title, .viewer_url, .uploaded_at] | @tsv' | grep -v DELETED
else
  jq -r '[.id, .title, .viewer_url, .uploaded_at] | @tsv' "$IMGLAB_LOG" | grep -v DELETED
fi
