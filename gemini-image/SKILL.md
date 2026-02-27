---
name: gemini-image
version: 0.2.0
description: "Generate and edit images with Gemini 3.1 Flash Image (Nano Banana 2) via third-party proxy. Supports text-to-image, image editing, multi-image composition (up to 14), aspect ratio control, and 1K/2K/4K resolution."
---

# Gemini Image Generation

Generate and edit images via Gemini 3.1 Flash Image (Nano Banana 2) through a third-party API proxy.

## Setup

Environment variables are auto-injected via OpenClaw `env.vars`:
- `GPTCLUB_API_KEY` — Required. API key for the proxy service.
- `GEMINI_API_KEY` — Fallback if `GPTCLUB_API_KEY` is not set.

> Optional config overrides in `~/.openclaw/openclaw.json`:
> - `skills."gemini-image".baseUrl` — Proxy base URL (default: `https://api.gptclubapi.xyz/gemini`)
> - `skills."gemini-image".model` — Model name (default: `gemini-3.1-flash-image`)

## Generate

```bash
uv run <skill_dir>/scripts/generate_image.py --prompt "description" --filename "output.png"
```

### Parameters

| Param | Required | Description |
|-------|----------|-------------|
| --prompt, -p | Yes | Image description / generation prompt |
| --filename, -f | Yes | Output filename (e.g., `2026-02-27-sunset.png`) |
| --resolution, -r | No | `1K` (default), `2K`, or `4K` |
| --aspect-ratio, -a | No | Aspect ratio (see below). Default: model decides. |
| --input-image, -i | No | Input image(s) for editing. Repeatable, up to 14. |
| --model, -m | No | Override model name |
| --base-url | No | Override proxy base URL |
| --api-key, -k | No | Override API key |

### Aspect Ratios

Supported values: `1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9`

```bash
uv run <skill_dir>/scripts/generate_image.py -p "vertical phone wallpaper" -f "wallpaper.png" -a 9:16
uv run <skill_dir>/scripts/generate_image.py -p "cinematic landscape" -f "landscape.png" -a 21:9 -r 4K
```

## Edit (single image)

```bash
uv run <skill_dir>/scripts/generate_image.py -p "make the sky purple" -f "output.png" -i "/path/to/input.png" -r 2K
```

Resolution auto-detects from input image dimensions when not explicitly set.

## Multi-image Composition (up to 14 images)

```bash
uv run <skill_dir>/scripts/generate_image.py -p "combine into one scene" -f "output.png" -i img1.png -i img2.png -i img3.png
```

## Model Capabilities

- **World knowledge**: Renders real-world subjects accurately using Gemini's knowledge base.
- **Text rendering**: Generates legible, accurate text within images. Great for mockups and cards.
- **Translation**: Can translate and localize text within images.
- **Character consistency**: Maintains appearance of up to 5 characters and 14 objects in a workflow.
- **Infographics**: Creates diagrams, flowcharts, and data visualizations from descriptions.
- **Production specs**: From 512px to 4K, multiple aspect ratios.

## Output

- The script prints a `MEDIA:` line for OpenClaw to auto-attach on supported chat providers.
- Do not read the image file back; report the saved path only.
- Use timestamps in filenames: `yyyy-mm-dd-hh-mm-ss-name.png`.
- Generation typically takes 15-45 seconds through the proxy.
