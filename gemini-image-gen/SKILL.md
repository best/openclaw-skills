---
name: gemini-image-gen
description: "Generate and edit images using the Gemini Image Generation API with provider fallback through GEMINI_IMAGE_CONFIG. Supports text-to-image, image editing, multi-image composition (up to 14 input images), aspect ratio control, and 1K/2K/4K resolution. Automatically falls back to alternate providers on failure. Use when the user asks to create, generate, draw, or edit images."
metadata:
  version: 1.1.1
---

# Gemini Image Generation

Generate and edit images via the bundled Python script with automatic provider fallback. The script only uses provider entries from `GEMINI_IMAGE_CONFIG` or `--config`; single-provider env/CLI overrides are intentionally unsupported.

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
| -m, --model | No | Override model ID across the provider chain |
| --config | No | Path to provider chain config file; defaults to `GEMINI_IMAGE_CONFIG` |

## Provider Fallback

The script is **config-only**: it requires a provider chain from `GEMINI_IMAGE_CONFIG` or `--config`. Do not use `GEMINI_API_KEY`, `GEMINI_BASE_URL`, `--api-key`, or `--base-url` single-provider overrides.

### Config File Schema

```json
{
  "providers": [
    {
      "name": "provider-label",
      "base_url": "https://proxy.example.com/gemini",
      "api_key": "<provider API key>",
      "model": "gemini-3.1-flash-image-preview"
    },
    {
      "name": "google-direct",
      "base_url": null,
      "api_key": "<provider API key>",
      "model": "gemini-3.1-flash-image-preview"
    }
  ]
}
```

- `api_key` may be stored directly in the private config file
- `api_key_env` is also supported if a deployment wants the config to reference an env var name instead
- Keep the config file outside the skill repo; never commit real keys
- `base_url: null`: use Google's official endpoint directly
- Providers tried top-to-bottom; first success wins
- `-m, --model` may override the model across the provider chain

### First-Time Setup

When using this skill and no `GEMINI_IMAGE_CONFIG` is configured yet:

1. Ask which Gemini API providers are available (proxy services, Google direct, etc.)
2. Create a config JSON following the schema above
3. Save it to a persistent path outside the skill directory
4. Set `GEMINI_IMAGE_CONFIG` to the config file path
5. Put actual keys in each provider's `api_key` field, or use `api_key_env` if env indirection is required

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
| `GEMINI_IMAGE_CONFIG` | Yes* | Path to provider-chain config JSON |
| provider `api_key` fields | Yes** | Actual provider API keys stored in the private config file |
| env vars named by `api_key_env` | No | Optional indirection alternative to inline `api_key` |
| `GEMINI_IMAGE_OUTPUT_DIR` | No | Output directory (default: `~/.openclaw/workspace/images`) |

* Or pass `--config /path/to/providers.json` for an explicit config path.
** Each provider needs either `api_key` or `api_key_env`.

## Prompt Writing

See [references/prompting.md](references/prompting.md) for templates and best practices.

Key principle: **describe the scene as a narrative paragraph**, not a keyword list.

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `No providers available` | Missing/empty config or provider key entries | Create `GEMINI_IMAGE_CONFIG` or pass `--config` |
| `All providers failed` | Every provider returned errors | Check API keys and model names |
| `No image was generated` | API returned text-only | Rephrase prompt; may trigger safety filters |
| First run slow (~10s) | `uv` downloading dependencies | Subsequent runs use cache |
