---
name: atlas-image-gen
description: "Generate text-to-image assets through Atlas Cloud with a single guarded submission and bounded result polling. Uses ATLASCLOUD_API_KEY, defaults to Flux Schnell, supports batches of up to four images, and saves remote outputs locally. Use when the user asks to create or generate images with Atlas Cloud."
metadata:
  version: 0.1.0
---

# Atlas Cloud Image Generation

Generate images through the Atlas Cloud asynchronous image API. The bundled script submits each requested batch exactly once, polls the returned prediction with bounded GET retries, downloads the completed images, and prints `MEDIA:` lines for supported chat platforms.

## Generate an Image

```bash
python3 <skill_dir>/scripts/generate_image.py \
  --prompt "a paper boat floating on a quiet blue pond" \
  --filename "paper-boat.png"
```

Generate up to four images in one API submission:

```bash
python3 <skill_dir>/scripts/generate_image.py \
  --prompt "minimal editorial illustration of a mountain observatory" \
  --filename "observatory.png" \
  --count 4 \
  --size 1024x1024
```

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `-p, --prompt` | Yes | Text description of the image |
| `-f, --filename` | Yes | Output filename; a timestamp is added automatically |
| `-n, --count` | No | Images in one submission, from 1 to 4 (default: 1) |
| `--size` | No | Output size as `WIDTHxHEIGHT` (default: `1024x1024`) |
| `--seed` | No | Integer seed; `-1` lets the model choose (default: `-1`) |
| `-m, --model` | No | Atlas Cloud image model ID |
| `--poll-interval` | No | Seconds between status checks (default: 2) |
| `--timeout` | No | Overall polling timeout in seconds (default: 300) |

The default model is `black-forest-labs/flux-schnell`. Override it with `--model` or `ATLASCLOUD_IMAGE_MODEL`. Check the live Atlas Cloud model catalog before selecting another model because schemas can differ.

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `ATLASCLOUD_API_KEY` | Yes | Atlas Cloud API key |
| `ATLASCLOUD_IMAGE_MODEL` | No | Default image model override |
| `ATLASCLOUD_API_BASE_URL` | No | API base URL (default: `https://api.atlascloud.ai`) |
| `ATLASCLOUD_IMAGE_OUTPUT_DIR` | No | Output directory (default: `~/.openclaw/workspace/images`) |

Keep API keys outside this repository and never include them in prompts, logs, or committed files.

## Reliability Rules

- A generation `POST` is never retried automatically. If submission fails, inspect the error before deciding whether to run a new paid request.
- Prediction and image-download `GET` requests use at most three attempts for transient network or server errors.
- Polling stops on a terminal failure or when `--timeout` is reached.
- Only HTTPS output URLs are downloaded.

## Output Handling

Plain filenames are written under `$ATLASCLOUD_IMAGE_OUTPUT_DIR/YYYY-MM/`. The script detects PNG, JPEG, GIF, and WebP output data, preserves the matching extension, and emits one `MEDIA:` line per saved image.

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `ATLASCLOUD_API_KEY is not set` | Missing credential | Export the key in the private runtime environment |
| `Generation submission failed` | The single POST was rejected or interrupted | Inspect the HTTP response; do not blindly rerun a billable request |
| `Prediction failed` | Atlas Cloud returned a terminal failure | Review the returned error or logs and adjust the prompt/model |
| `Timed out waiting for prediction` | The job did not finish within the limit | Query the known prediction separately before considering a new submission |
| `No HTTPS image outputs` | Unexpected or incomplete API response | Verify the selected model's current schema |
