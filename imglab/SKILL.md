---
name: imglab
description: Upload, manage, and delete images on ImgLab (Chevereto V4) image hosting. Use when generating images, screenshots, or any visual content that should be hosted and shared via a permanent URL. Also use for listing or deleting previously uploaded images. Triggers on image generation, upload requests, image management, or when a shareable image link is needed.
---

# ImgLab Image Uploader

Upload images to imglab.cc (Chevereto V4) and return permanent, shareable links.

## Setup

Load config before running any script:

```bash
set -a; source ~/.openclaw/workspace/.imglab.env; set +a
```

## Upload

```bash
bash <skill_dir>/scripts/upload.sh <file_path> [title] [description] [tags] [album_id]
```

Returns JSON with:
- `viewer_url` — shareable page link (give to user)
- `direct_url` — direct image file URL (for embedding/download)
- `thumb_url` — thumbnail
- `delete_url` — one-time deletion link
- `id` — encoded image ID

All uploads are logged to `memory/imglab-uploads.jsonl` with delete URLs for later management.

### Metadata Convention for AI-Generated Images

- **title**: Short descriptive name
- **description**: Generation details:
  ```
  Prompt: <full generation prompt>
  Model: <model name>
  Generated: <YYYY-MM-DD>
  Request: <user's original request>
  ```
- **tags**: Always include `ai-generated,openclaw` plus model name
- **album_id**: Default `VBQ` (OpenClaw album, from env)

## Delete

```bash
bash <skill_dir>/scripts/delete.sh <image_id_or_delete_url>
```

Accepts either an image ID (looks up delete_url from log) or a full delete URL.

## List Uploads

```bash
bash <skill_dir>/scripts/list.sh                    # all uploads
bash <skill_dir>/scripts/list.sh --recent 10         # last 10
bash <skill_dir>/scripts/list.sh --search "keyword"  # search by title
```

## After Upload

Always return both URLs to the user:
- **Viewer page**: `viewer_url` (browsable, shows metadata)
- **Direct link**: `direct_url` (direct image file, for embedding)
