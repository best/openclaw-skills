#!/usr/bin/env bash
# ImgLab image deleter
# Usage: delete.sh <image_id_or_delete_url>
# - If a full delete_url is given, use it directly
# - If an image ID is given, look up delete_url from upload log
set -euo pipefail

IMGLAB_LOG="${IMGLAB_LOG:-$HOME/.openclaw/workspace/memory/imglab-uploads.jsonl}"

INPUT="${1:?Usage: delete.sh <image_id_or_delete_url>}"

# Determine delete URL
if [[ "$INPUT" == http* ]]; then
  DELETE_URL="$INPUT"
else
  # Look up from log
  if [[ ! -f "$IMGLAB_LOG" ]]; then
    echo "Error: No upload log found at $IMGLAB_LOG" >&2
    exit 1
  fi
  DELETE_URL=$(grep "\"id\":\"$INPUT\"" "$IMGLAB_LOG" | tail -1 | jq -r '.delete_url // empty')
  if [[ -z "$DELETE_URL" ]]; then
    echo "Error: Image ID '$INPUT' not found in upload log" >&2
    exit 1
  fi
fi

echo "Deleting: $DELETE_URL"
HTTP_CODE=$(curl -sL --max-time 15 "$DELETE_URL" -o /dev/null -w "%{http_code}")

if [[ "$HTTP_CODE" == "404" || "$HTTP_CODE" == "200" ]]; then
  echo "Deleted successfully (HTTP $HTTP_CODE)"
  # Mark as deleted in log if possible
  if [[ -f "$IMGLAB_LOG" ]]; then
    # Extract image ID from delete URL
    IMG_ID=$(echo "$DELETE_URL" | grep -oP '/image/\K[^/]+')
    if [[ -n "$IMG_ID" ]]; then
      sed -i "s/\"id\":\"$IMG_ID\"/\"id\":\"${IMG_ID}_DELETED\"/" "$IMGLAB_LOG" 2>/dev/null || true
    fi
  fi
else
  echo "Delete may have failed (HTTP $HTTP_CODE)" >&2
  exit 1
fi
