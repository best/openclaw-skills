---
name: chevereto-upload
version: 0.4.0
description: "Upload images to a Chevereto V4 image hosting service using a local config file for permanent, shareable URLs. Use when images (AI-generated, screenshots, or any visual content) need to be hosted, archived, or shared via a link. Also supports listing and deleting uploaded images."
---

# Chevereto Upload

Upload images to a Chevereto V4 instance via the bundled shell script. The script handles API authentication, file upload, metadata tagging, and upload logging.

## How to Upload

Run the upload script with the image path and metadata:

```bash
bash <skill_dir>/scripts/upload.sh <file_path> "<title>" "<description>" "<tags>" [album_id]
```

Provide title, description, and tags on every upload — these make images discoverable and traceable.

### Example: AI-Generated Image

```bash
bash <skill_dir>/scripts/upload.sh /tmp/2026-03-01-14-30-00-sunset.png \
  "Sunset Over Cyberpunk City" \
  "Prompt: A dramatic sunset over a neon-lit cyberpunk cityscape with flying cars
Model: gemini-3.1-flash-image
Generated: 2026-03-01
Request: cyberpunk sunset wallpaper" \
  "ai-generated,openclaw,gemini,cyberpunk,sunset"
```

### Example: Screenshot or Other Image

```bash
bash <skill_dir>/scripts/upload.sh /tmp/screenshot.png \
  "Dashboard Overview Q1" \
  "Screenshot of the analytics dashboard showing Q1 2026 metrics" \
  "screenshot,dashboard,analytics"
```

### Metadata Guide

| Field | How to Fill |
|-------|-------------|
| title | Short descriptive name in English (e.g., "Cherry Blossom Phone Wallpaper") |
| description | For AI images: include Prompt, Model, Generated date, and user's original Request. For other images: describe content and context |
| tags | Comma-separated keywords. AI images always include `ai-generated,openclaw` plus model name and style tags |

**Metadata rules:**
- **Never include proxy/third-party service info** in descriptions — only the model name (e.g., "gemini-3-pro-image", not "via gptclub proxy")
- **Always upload via the script** — do not use raw `curl` against the API. The script ensures all metadata fields (delete_url, dimensions, size) are logged to `chevereto-uploads.jsonl`
- **Non-ASCII titles** (Chinese, etc.) are handled gracefully — the script falls back to a timestamp-based filename when the title has no ASCII-safe characters

### Response

The script outputs JSON with:

- `viewer_url` — shareable page link (browsable, shows metadata)
- `direct_url` — direct image file URL (for embedding)
- `thumb_url` — thumbnail URL
- `delete_url` — one-time deletion link

Return both `viewer_url` and `direct_url` to the user after upload.

All uploads are automatically logged to `memory/chevereto-uploads.jsonl`.

## List Uploads

```bash
bash <skill_dir>/scripts/list.sh                     # all uploads
bash <skill_dir>/scripts/list.sh --recent 10          # last 10
bash <skill_dir>/scripts/list.sh --search "keyword"   # search by title
```

## Delete

```bash
bash <skill_dir>/scripts/delete.sh <image_id_or_delete_url>
```

Accepts an image ID (looks up delete_url from the upload log) or a full delete URL.

## Configuration

The upload script reads a local JSON config file. Default path:

```bash
/root/.openclaw/config/chevereto-upload.json
```

Optional override: set `CHEVERETO_CONFIG` to another config file path for one command. Do **not** store the API key in OpenClaw `env.vars`.

```json
{
  "url": "https://imglab.cc",
  "api_key": "<chevereto api key>",
  "album_id": "VBQ",
  "log_file": "/root/.openclaw/workspace/memory/chevereto-uploads.jsonl"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `api_key` | Yes | User API key |
| `url` | No | Site URL (default: `https://imglab.cc`) |
| `album_id` | No | Default album ID for uploads |
| `log_file` | No | Upload log path |
