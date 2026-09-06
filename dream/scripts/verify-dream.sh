#!/usr/bin/env bash
# Use the same character policy and file inventory as Dream.
set -euo pipefail
workspace_dir="${1:-${OPENCLAW_WORKSPACE:-$PWD}}"
exec node "$(dirname -- "${BASH_SOURCE[0]}")/t0-budget-check.mjs" "$workspace_dir" --json
