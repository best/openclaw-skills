---
name: chevereto-upload
version: 0.2.0
description: "Upload, manage, and delete images on any Chevereto V4 instance. Use when generating images, screenshots, or any visual content that should be hosted and shared via a permanent URL. Also handles listing and deleting previously uploaded images."
---

# Chevereto Upload

Upload images to a Chevereto V4 instance and return permanent, shareable links.

## Setup

Environment variables are auto-injected via OpenClaw `env.vars`:
- `CHEVERETO_API_KEY` — Required. User API key from `<your-site>/settings/api`
- `CHEVERETO_URL` — Site URL (default: `https://imglab.cc`)
- `CHEVERETO_ALBUM_ID` — Default album ID (optional)

> To use with a different Chevereto instance, just change `CHEVERETO_URL` and `CHEVERETO_API_KEY`.

## Upload

```bash
bash <skill_dir>/scripts/upload.sh <file_path> [title] [description] [tags] [album_id]
```

### Parameters

| Param | Required | Description |
|-------|----------|-------------|
| file_path | Yes | Local path to image file |
| title | No | Image title (also used as filename: lowercased, hyphenated) |
| description | No | Detailed description with generation metadata |
| tags | No | Comma-separated tags |
| album_id | No | Target album (overrides `CHEVERETO_ALBUM_ID` env) |

### Response

JSON object with key fields:
- `viewer_url` — Shareable page link (browsable, shows metadata)
- `direct_url` — Direct image file URL (for embedding/download)
- `thumb_url` — Thumbnail URL
- `delete_url` — One-time deletion link
- `id` — Encoded image ID

All uploads are logged to `memory/chevereto-uploads.jsonl` for later management.

### Metadata Convention for AI-Generated Images

- **title**: Short descriptive name in English (e.g. "Sunset Over Cyberpunk City")
- **description**: Include generation details:
  ```
  Prompt: <full generation prompt>
  Model: <model name and version>
  Generated: <YYYY-MM-DD>
  Request: <what the user originally asked for>
  ```
- **tags**: Always include `ai-generated,openclaw` plus model name and style tags

## Delete

```bash
bash <skill_dir>/scripts/delete.sh <image_id_or_delete_url>
```

Accepts either an image ID (looks up delete_url from the upload log) or a full delete URL.

## List Uploads

```bash
bash <skill_dir>/scripts/list.sh                     # all uploads
bash <skill_dir>/scripts/list.sh --recent 10          # last 10
bash <skill_dir>/scripts/list.sh --search "keyword"   # search by title
```

## After Upload

Always return both URLs to the user:
- **Viewer page**: `viewer_url` (browsable, shows full metadata)
- **Direct link**: `direct_url` (direct image file, for embedding)
