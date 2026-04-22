---
name: openai-image-gen
version: 1.1.0
description: "Generate and edit images with the OpenAI Image API, defaulting to gpt-image-2. Supports text-to-image, multi-image editing/composition (up to 16 input images), mask-based edits, size/quality/background/output-format control, and provider fallback through a config file. Use when the user asks to create, draw, generate, or edit images with OpenAI / GPT Image models, especially when the built-in image tool has not exposed the latest OpenAI image model yet."
---

# OpenAI Image Generation

Generate and edit images via the bundled Python script with `gpt-image-2` as the default model.

Use this skill when OpenClaw's built-in `image_generate` tool does not yet expose the desired OpenAI image model, but a direct OpenAI-compatible Image API endpoint is available.

## How to Generate

```bash
uv run <skill_dir>/scripts/generate_image.py \
  -p "a moonlit courtyard with cherry blossoms" \
  -f "courtyard.png"
```

Generate multiple images:

```bash
uv run <skill_dir>/scripts/generate_image.py \
  -p "minimal poster of a red fox in snowfall" \
  -f "fox-poster.png" \
  -n 3
```

Control size / quality / format / background:

```bash
uv run <skill_dir>/scripts/generate_image.py \
  -p "transparent icon of a white crane in flight" \
  -f "crane.webp" \
  --size 1024x1024 \
  --quality high \
  --background transparent \
  --output-format webp \
  --output-compression 90
```

Generate in **4K** (gpt-image-2 extended):

```bash
uv run <skill_dir>/scripts/generate_image.py \
  -p "a photorealistic UI screenshot" \
  -f "screenshot-4k.png" \
  --size 3840x2160 \
  --quality high
```

## How to Edit

Edit one existing image:

```bash
uv run <skill_dir>/scripts/generate_image.py \
  -p "replace the background with a misty bamboo forest" \
  -f "bamboo-scene.png" \
  -i /path/to/input.png
```

Edit with multiple reference images (up to 16):

```bash
uv run <skill_dir>/scripts/generate_image.py \
  -p "merge these into one coherent cinematic portrait" \
  -f "merged-portrait.png" \
  -i face.png -i outfit.png -i background.png
```

Edit with a mask:

```bash
uv run <skill_dir>/scripts/generate_image.py \
  -p "only replace the masked area with blooming sakura branches" \
  -f "masked-edit.png" \
  -i source.png \
  --mask mask.png
```

## Parameters

| Param | Required | Description |
|-------|----------|-------------|
| `-p, --prompt` | Yes | Image description or edit instruction |
| `-f, --filename` | Yes | Output filename. Timestamp prefix auto-added |
| `-i, --input-image` | No | Input image path. Repeatable, up to 16 |
| `--mask` | No | Optional PNG mask for edit mode |
| `-n, --count` | No | Number of images to generate, 1-10 |
| `--size` | No | `auto` `1024x1024` `1536x1024` `1024x1536` `2048x2048` `2048x1152` `3840x2160` (4K) `2160x3840` (4K) |
| `--quality` | No | `auto` `low` `medium` `high` |
| `--background` | No | `auto` `transparent` `opaque` |
| `--output-format` | No | `png` `webp` `jpeg` |
| `--output-compression` | No | `0-100`, only for `webp` / `jpeg` |
| `--moderation` | No | Generation-only moderation level: `auto` or `low` |
| `--input-fidelity` | No | Edit-only fidelity: `low` or `high` |
| `-m, --model` | No | Override model ID, e.g. `gpt-image-2` |
| `--base-url` | No | Override API endpoint (single-provider mode) |
| `-k, --api-key` | No | Override API key (single-provider mode) |
| `--config` | No | Path to provider chain config JSON |

## Provider Fallback

By default the script runs in **single-provider mode** using `OPENAI_IMAGE_API_KEY` (+ optional `OPENAI_IMAGE_BASE_URL`).

To enable automatic fallback across multiple OpenAI-compatible providers, point the script at a config file via `--config` or the `OPENAI_IMAGE_CONFIG` env var.

### Config File Schema

```json
{
  "providers": [
    {
      "name": "openai-direct",
      "base_url": null,
      "api_key_env": "OPENAI_IMAGE_API_KEY",
      "model": "gpt-image-2"
    },
    {
      "name": "compatible-proxy",
      "base_url": "https://proxy.example.com/v1",
      "api_key_env": "PROXY_API_KEY",
      "model": "gpt-image-2"
    }
  ]
}
```

- `api_key_env` stores the **env var name**, not the key itself
- `base_url: null` means OpenAI direct
- Providers are tried top-to-bottom; first success wins
- CLI overrides (`-k`, `--base-url`) bypass the chain entirely

### First-Time Setup

When using this skill and no `OPENAI_IMAGE_CONFIG` is configured yet:

1. Ask which OpenAI-compatible image endpoints are available
2. Create a config JSON following the schema above
3. Save it to a persistent path outside the skill directory
4. Set `OPENAI_IMAGE_CONFIG` so the script can find it automatically

Keep this skill's config separate from general-purpose `OPENAI_BASE_URL` / `OPENAI_API_KEY` setups when those are already used for other APIs or proxies.

## Error Classification

- **Retryable** → try next provider: `408` `409` `429` `500` `502` `503` `504`, timeout, connection failures
- **Auth errors** → skip provider and continue: `401` `403`
- **Non-retryable** → fail immediately: bad request, invalid params, safety rejection

## Output Handling

- Prints `MEDIA:` lines for auto-attachment on supported chat platforms
- Report the saved file path to the user; do not read generated images back into context
- For permanent hosting, use the `chevereto-upload` skill after generation
- Plain filename output goes to `$OPENAI_IMAGE_OUTPUT_DIR/YYYY-MM/timestamp-name.ext`

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_IMAGE_API_KEY` | Yes* | Primary image-provider API key |
| `OPENAI_IMAGE_BASE_URL` | No | Primary image endpoint override |
| `OPENAI_IMAGE_MODEL` | No | Default model for single-provider mode (`gpt-image-2`) |
| `OPENAI_IMAGE_OUTPUT_DIR` | No | Output directory (default: `~/.openclaw/workspace/images`) |
| `OPENAI_IMAGE_CONFIG` | No | Path to provider-chain config JSON |

\* Required unless `--api-key` is provided or the config file references a valid provider key.

## Prompt Writing

See [references/prompting.md](references/prompting.md) for templates and best practices.

Key principle: **write one clear scene paragraph**, and for edits explicitly say what must remain unchanged.

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `No providers configured` | Missing env vars or config file | Set `OPENAI_IMAGE_API_KEY` or create `OPENAI_IMAGE_CONFIG` |
| `All providers failed` | Every provider returned errors | Check endpoint compatibility, keys, and model name |
| `transparent background requires png or webp` | Invalid format/background combo | Switch output format to `png` or `webp` |
| `API response contained no savable image data` | Proxy returned unexpected payload | Try OpenAI direct or a fully compatible endpoint |
| `First run slow (~10s)` | `uv` downloading dependencies | Subsequent runs use cache |
