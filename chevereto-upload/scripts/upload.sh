#!/usr/bin/env bash
# Chevereto V4 image uploader
# Usage: upload.sh <file_path> [title] [description] [tags] [album_id]
set -euo pipefail

# --- Config ---
CHEVERETO_CONFIG="${CHEVERETO_CONFIG:-/root/.openclaw/config/chevereto-upload.json}"
if [[ ! -f "$CHEVERETO_CONFIG" ]]; then
  echo "Error: Chevereto config not found: $CHEVERETO_CONFIG" >&2
  exit 1
fi

SITE_URL="$(jq -r '.url // "https://imglab.cc"' "$CHEVERETO_CONFIG")"
API_KEY="$(jq -r '.api_key // empty' "$CHEVERETO_CONFIG")"
DEFAULT_ALBUM_ID="$(jq -r '.album_id // ""' "$CHEVERETO_CONFIG")"
LOG_FILE="$(jq -r --arg default "$HOME/.openclaw/workspace/memory/chevereto-uploads.jsonl" '.log_file // .log // $default' "$CHEVERETO_CONFIG")"

if [[ -z "$API_KEY" ]]; then
  echo "Error: Chevereto config missing api_key: $CHEVERETO_CONFIG" >&2
  exit 1
fi

# --- Args ---
FILE_PATH="${1:?Usage: upload.sh <file_path> [title] [description] [tags] [album_id]}"
ORIGINAL_FILE_PATH="$FILE_PATH"  # preserve original path for logging
TITLE="${2:-}"
DESCRIPTION="${3:-}"
TAGS="${4:-}"
ALBUM_ID="${5:-$DEFAULT_ALBUM_ID}"

# --- Validate ---
if [[ ! -f "$FILE_PATH" ]]; then
  echo "Error: File not found: $FILE_PATH" >&2
  exit 1
fi

# --- Rename file to meaningful name based on title ---
RENAMED_PATH=""
if [[ -n "$TITLE" ]]; then
  EXT="${FILE_PATH##*.}"
  # Title → lowercase, spaces/special chars → hyphens, trim
  SAFE_NAME=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g; s/--*/-/g; s/^-//; s/-$//')
  # Fallback: non-ASCII titles (e.g. Chinese) produce empty SAFE_NAME
  if [[ -z "$SAFE_NAME" || ${#SAFE_NAME} -lt 3 ]]; then
    SAFE_NAME="upload-$(date +%Y%m%d-%H%M%S)"
  fi
  RENAMED_PATH="/tmp/${SAFE_NAME}.${EXT}"
  cp "$FILE_PATH" "$RENAMED_PATH"
  FILE_PATH="$RENAMED_PATH"
fi

# --- Build curl args ---
CURL_ARGS=(
  -s --fail-with-body
  -X POST
  -H "X-API-Key: $API_KEY"
  -F "source=@${FILE_PATH}"
  -F "format=json"
)

[[ -n "$TITLE" ]] && CURL_ARGS+=(-F "title=${TITLE}")
[[ -n "$DESCRIPTION" ]] && CURL_ARGS+=(-F "description=${DESCRIPTION}")
[[ -n "$TAGS" ]] && CURL_ARGS+=(-F "tags=${TAGS}")
[[ -n "$ALBUM_ID" ]] && CURL_ARGS+=(-F "album_id=${ALBUM_ID}")

# --- Upload ---
RESPONSE=$(curl "${CURL_ARGS[@]}" "${SITE_URL}/api/1/upload" 2>&1)
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

# --- Cleanup temp renamed file ---
[[ -n "$RENAMED_PATH" && -f "$RENAMED_PATH" ]] && rm -f "$RENAMED_PATH"

# --- Log upload for management ---
mkdir -p "$(dirname "$LOG_FILE")"
# --- Detect agent from workspace path ---
AGENT_ID="${CHEVERETO_AGENT:-}"
if [[ -z "$AGENT_ID" ]]; then
  case "$PWD" in
    */workspace-*) AGENT_ID="${PWD##*workspace-}" ;;
    */workspace)   AGENT_ID="main" ;;
    *)             AGENT_ID="unknown" ;;
  esac
fi
LOG_ENTRY=$(echo "$RESULT" | jq -c \
  --arg uploaded_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg agent "$AGENT_ID" \
  --arg local_file "$ORIGINAL_FILE_PATH" \
  --arg description "$DESCRIPTION" \
  --arg tags "$TAGS" \
  '. + {uploaded_at: $uploaded_at, agent: $agent, local_file: $local_file, description: $description, tags: $tags}')
echo "$LOG_ENTRY" >> "$LOG_FILE"
