#!/usr/bin/env bash
# List uploaded images from the local log
# Usage: list.sh [--recent N] [--search TERM] [--agent AGENT_ID]
set -euo pipefail

CHEVERETO_LOG="${CHEVERETO_LOG:-$HOME/.openclaw/workspace/memory/chevereto-uploads.jsonl}"

if [[ ! -f "$CHEVERETO_LOG" ]]; then
  echo "No uploads found (log file does not exist)"
  exit 0
fi

FLAG="${1:-}"
VALUE="${2:-}"
FLAG2="${3:-}"
VALUE2="${4:-}"

AGENT_FILTER=""
if [[ "$FLAG" == "--agent" ]]; then
  AGENT_FILTER="$VALUE"
  FLAG="$FLAG2"
  VALUE="$VALUE2"
elif [[ "$FLAG2" == "--agent" ]]; then
  AGENT_FILTER="$VALUE2"
fi

filter_agent() {
  if [[ -n "$AGENT_FILTER" ]]; then
    jq -r "select(.agent == \"$AGENT_FILTER\") | [.id, .agent, .title, .viewer_url, .uploaded_at] | @tsv" | grep -v DELETED
  else
    jq -r '[.id, .agent, .title, .viewer_url, .uploaded_at] | @tsv' | grep -v DELETED
  fi
}

if [[ "$FLAG" == "--recent" && -n "$VALUE" ]]; then
  tail -n "$VALUE" "$CHEVERETO_LOG" | filter_agent
elif [[ "$FLAG" == "--search" && -n "$VALUE" ]]; then
  grep -i "$VALUE" "$CHEVERETO_LOG" | filter_agent
else
  cat "$CHEVERETO_LOG" | filter_agent
fi
