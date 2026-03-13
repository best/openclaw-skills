---
name: gemini-image-gen
version: 1.0.0
description: "Generate and edit images using the Gemini Image Generation API with provider fallback. Supports text-to-image, image editing, multi-image composition (up to 14 input images), aspect ratio control, and 1K/2K/4K resolution. Automatically falls back to alternate providers on failure. Use when the user asks to create, generate, draw, or edit images."
---

# Gemini Image Generation

Generate and edit images via the bundled Python script with automatic provider fallback.

## How to Generate

```bash
uv run <skill_dir>/scripts/generate_image.py -p "description" -f "name.png"
```

With aspect ratio and resolution:

```bash
uv run <skill_dir>/scripts/generate_image.py \
  -p "cherry blossoms in spring breeze" -f "blossoms.png" -a 9:16 -r 2K
```

Edit an existing image:

```bash
uv run <skill_dir>/scripts/generate_image.py \
  -p "make the sky purple" -f "purple-sky.png" -i /path/to/input.png
```

Compose multiple images (up to 14):

```bash
uv run <skill_dir>/scripts/generate_image.py \
  -p "combine into a unified scene" -f "combined.png" -i img1.png -i img2.png
```

### Parameters

| Param | Required | Description |
|-------|----------|-------------|
| -p, --prompt | Yes | Image description or editing instruction |
| -f, --filename | Yes | Output filename. Timestamp prefix auto-added |
| -r, --resolution | No | `1K` (default), `2K`, or `4K`. Auto-detected from input images |
| -a, --aspect-ratio | No | `1:1` `2:3` `3:2` `3:4` `4:3` `4:5` `5:4` `9:16` `16:9` `21:9` |
| -i, --input-image | No | Input image path. Repeatable, up to 14 |
| -m, --model | No | Override model ID (bypasses provider config) |
| --base-url | No | Override API endpoint (single-provider mode) |
| -k, --api-key | No | Override API key (single-provider mode) |
| --config | No | Path to provider chain config file |

## Provider Fallback

By default the script runs in **single-provider mode** using `GEMINI_API_KEY` (+ optional `GEMINI_BASE_URL`). To enable automatic fallback across multiple providers, point the script at a config file via `--config` or the `GEMINI_IMAGE_CONFIG` env var.

### Config File Schema

```json
{
  "providers": [
    {
      "name": "provider-label",
      "base_url": "https://proxy.example.com/gemini",
      "api_key_env": "ENV_VAR_NAME_FOR_API_KEY",
      "model": "gemini-3.1-flash-image"
    },
    {
      "name": "google-direct",
      "base_url": null,
      "api_key_env": "GOOGLE_GEMINI_API_KEY",
      "model": "gemini-3.1-flash-image"
    }
  ]
}
```

- `api_key_env`: environment variable **name** (not the key itself) — file is safe to commit
- `base_url: null`: use Google's official endpoint directly
- Providers tried top-to-bottom; first success wins
- CLI overrides (`-k`, `--base-url`) bypass the chain entirely

### First-Time Setup

When using this skill and no `GEMINI_IMAGE_CONFIG` is configured yet:

1. Ask the user which Gemini API providers they have access to (proxy services, Google direct, etc.)
2. Generate a config JSON following the schema above, populated with their providers and env var names
3. Ask the user where to save the file (a persistent path outside the skill directory)
4. Configure the env var so the script finds it automatically:
   - **OpenClaw**: add `GEMINI_IMAGE_CONFIG` to `env.vars` in `~/.openclaw/openclaw.json` — all agents pick it up via exec injection
   - **Standalone**: `export GEMINI_IMAGE_CONFIG=/path/to/config.json` in shell profile

Without a config file, the script falls back to single-provider mode using `GEMINI_API_KEY` (+ optional `GEMINI_BASE_URL`), which requires no setup beyond setting those env vars.

### Error Classification

- **Retryable** (→ next provider): `429` `500` `502` `503`, timeout, connection errors
- **Non-retryable** (→ fail immediately): `400` bad request, safety filters, invalid params
- **Auth errors** (`401`/`403`): skip provider, try next

## Output Handling

- Prints `MEDIA:` line for auto-attachment on supported chat platforms
- Report the saved file path to the user. Do not read the image back into context
- For permanent hosting, use the `chevereto-upload` skill after generation
- RGBA images auto-converted to RGB (white background)

### Output Directory

Plain filename → `$GEMINI_IMAGE_OUTPUT_DIR/YYYY-MM/timestamp-name.png`

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes* | Primary provider API key |
| `GOOGLE_GEMINI_API_KEY` | No | Fallback provider API key |
| `GEMINI_BASE_URL` | No | Primary endpoint (fallback mode only) |
| `GEMINI_IMAGE_OUTPUT_DIR` | No | Output directory (default: `~/.openclaw/workspace/images`) |
| `GEMINI_IMAGE_CONFIG` | No | Path to providers.json override |

*Required unless `--api-key` is provided or providers.json has a valid provider.

## Prompt Writing

See [references/prompting.md](references/prompting.md) for templates and best practices.

Key principle: **describe the scene as a narrative paragraph**, not a keyword list.

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `No providers available` | No API keys set | Set env vars or use `-k` |
| `All providers failed` | Every provider returned errors | Check API keys and model names |
| `No image was generated` | API returned text-only | Rephrase prompt; may trigger safety filters |
| First run slow (~10s) | `uv` downloading dependencies | Subsequent runs use cache |
