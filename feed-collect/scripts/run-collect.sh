#!/usr/bin/env bash
# run-collect.sh — cron-safe wrapper for AI Feed collection.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/feedctl.py" --repo "${FEED_REPO:?FEED_REPO is required}" collect --commit --push "$@"
