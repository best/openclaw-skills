---
name: chevereto-upload
version: 0.3.0
description: "Upload images to a Chevereto V4 image hosting service for permanent, shareable URLs. Use when images (AI-generated, screenshots, or any visual content) need to be hosted, archived, or shared via a link. Also supports listing and deleting uploaded images."
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

Environment variables (auto-injected via OpenClaw `env.vars`):

| Variable | Required | Description |
|----------|----------|-------------|
| `CHEVERETO_API_KEY` | Yes | User API key |
| `CHEVERETO_URL` | No | Site URL (default: `https://imglab.cc`) |
| `CHEVERETO_ALBUM_ID` | No | Default album ID for uploads |
