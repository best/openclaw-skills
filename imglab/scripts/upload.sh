#!/usr/bin/env bash
# ImgLab (Chevereto V4) image uploader
# Usage: upload.sh <file_path> [title] [description] [tags] [album_id]
set -euo pipefail

# --- Config ---
IMGLAB_URL="${IMGLAB_URL:-https://imglab.cc}"
IMGLAB_API_KEY="${IMGLAB_API_KEY:?IMGLAB_API_KEY is required}"
IMGLAB_ALBUM_ID="${IMGLAB_ALBUM_ID:-}"
IMGLAB_LOG="${IMGLAB_LOG:-$HOME/.openclaw/workspace/memory/imglab-uploads.jsonl}"

# --- Args ---
FILE_PATH="${1:?Usage: upload.sh <file_path> [title] [description] [tags] [album_id]}"
TITLE="${2:-}"
DESCRIPTION="${3:-}"
TAGS="${4:-}"
ALBUM_ID="${5:-$IMGLAB_ALBUM_ID}"

# --- Validate ---
if [[ ! -f "$FILE_PATH" ]]; then
  echo "Error: File not found: $FILE_PATH" >&2
  exit 1
fi

# --- Rename file to meaningful name based on title ---
if [[ -n "$TITLE" ]]; then
  EXT="${FILE_PATH##*.}"
  # Title → lowercase, spaces/special chars → hyphens, trim
  SAFE_NAME=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g; s/--*/-/g; s/^-//; s/-$//')
  RENAMED_PATH="/tmp/${SAFE_NAME}.${EXT}"
  cp "$FILE_PATH" "$RENAMED_PATH"
  FILE_PATH="$RENAMED_PATH"
fi

# --- Build curl args ---
CURL_ARGS=(
  -s --fail-with-body
  -X POST
  -H "X-API-Key: $IMGLAB_API_KEY"
  -F "source=@${FILE_PATH}"
  -F "format=json"
)

[[ -n "$TITLE" ]] && CURL_ARGS+=(-F "title=${TITLE}")
[[ -n "$DESCRIPTION" ]] && CURL_ARGS+=(-F "description=${DESCRIPTION}")
[[ -n "$TAGS" ]] && CURL_ARGS+=(-F "tags=${TAGS}")
[[ -n "$ALBUM_ID" ]] && CURL_ARGS+=(-F "album_id=${ALBUM_ID}")

# --- Upload ---
RESPONSE=$(curl "${CURL_ARGS[@]}" "${IMGLAB_URL}/api/1/upload" 2>&1)
EXIT_CODE=$?

if [[ $EXIT_CODE -ne 0 ]]; then
  echo "Upload failed (curl exit $EXIT_CODE):" >&2
  echo "$RESPONSE" >&2
  exit 1
fi

# --- Check status ---
STATUS=$(echo "$RESPONSE" | jq -r '.status_code // empty')
if [[ "$STATUS" != "200" ]]; then
  ERROR_MSG=$(echo "$RESPONSE" | jq -r '.error.message // "Unknown error"')
  echo "Upload failed: $ERROR_MSG" >&2
  echo "$RESPONSE" >&2
  exit 1
fi

# --- Extract and output ---
RESULT=$(echo "$RESPONSE" | jq '{
  status: .status_code,
  id: .image.id_encoded,
  viewer_url: .image.url_viewer,
  direct_url: .image.image.url,
  display_url: .image.display_url,
  thumb_url: .image.thumb.url,
  title: .image.title,
  width: .image.width,
  height: .image.height,
  size: .image.size,
  size_formatted: .image.size_formatted,
  delete_url: .image.delete_url
}')

echo "$RESULT"

# --- Log upload for management ---
mkdir -p "$(dirname "$IMGLAB_LOG")"
LOG_ENTRY=$(echo "$RESULT" | jq -c ". + {uploaded_at: \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\", local_file: \"$FILE_PATH\"}")
echo "$LOG_ENTRY" >> "$IMGLAB_LOG"
