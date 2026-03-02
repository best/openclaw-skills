---
name: gemini-imagegen
version: 0.3.2
description: "Generate and edit images using the Gemini Image Generation API. Supports text-to-image, image editing, multi-image composition (up to 14 input images), aspect ratio control, and 1K/2K/4K resolution. Use when the user asks to create, generate, draw, or edit images."
---

# Gemini Image Generation

Generate and edit images using the Gemini Image Generation API via the bundled Python script.

**Default model:** `gemini-3.1-flash-image` (override via `-m` or `GEMINI_IMAGE_MODEL`).

## How to Generate

Run the script with a prompt and output filename:

```bash
uv run <skill_dir>/scripts/generate_image.py -p "description" -f "descriptive-name.png"
```

The script handles authentication, API communication, response parsing, image saving, and auto-organizes output files with timestamp prefixes into monthly directories.

### Examples

Text-to-image:

```bash
uv run <skill_dir>/scripts/generate_image.py \
  -p "a serene mountain lake at sunset with reflections" \
  -f "mountain-lake.png"
```

With aspect ratio and resolution:

```bash
uv run <skill_dir>/scripts/generate_image.py \
  -p "phone wallpaper of cherry blossoms in spring breeze" \
  -f "cherry-blossoms.png" \
  -a 9:16 -r 2K
```

Edit an existing image:

```bash
uv run <skill_dir>/scripts/generate_image.py \
  -p "make the sky purple and add northern lights" \
  -f "purple-sky.png" \
  -i /path/to/input.png
```

Compose multiple images (up to 14):

```bash
uv run <skill_dir>/scripts/generate_image.py \
  -p "combine these photos into a unified scene" \
  -f "combined.png" \
  -i img1.png -i img2.png -i img3.png
```

### Parameters

| Param | Required | Description |
|-------|----------|-------------|
| -p, --prompt | Yes | Image description or editing instruction |
| -f, --filename | Yes | Output filename (e.g., `mountain-lake.png`). Timestamp prefix auto-added |
| -r, --resolution | No | `1K` (default), `2K`, or `4K`. Auto-detected from input images (see below) |
| -a, --aspect-ratio | No | `1:1` `2:3` `3:2` `3:4` `4:3` `4:5` `5:4` `9:16` `16:9` `21:9` |
| -i, --input-image | No | Input image path for editing/composition. Repeatable, up to 14 |
| -m, --model | No | Override model ID (default: `gemini-3.1-flash-image`) |
| --base-url | No | Override API endpoint URL |
| -k, --api-key | No | Override API key |

### Auto-Resolution for Input Images

When editing or composing images (`-i`), the script **auto-detects output resolution** from the largest input dimension if `-r` is not explicitly set:

| Max input dimension | Auto-resolution |
|---------------------|-----------------|
| ≥ 3000px | 4K |
| ≥ 1500px | 2K |
| < 1500px | 1K |

This prevents quality loss when editing high-resolution inputs. To override, specify `-r` explicitly.

## Output Handling

- The script saves the image and prints a `MEDIA:` line for auto-attachment on supported chat platforms.
- Report the saved file path to the user. Do not read the generated image file back into the conversation.
- If the image should be permanently hosted, use the `chevereto-upload` skill as a separate step after generation.
- RGBA images are automatically converted to RGB (composited on white background) for PNG output.

### Output Directory

When `-f` is a plain filename (no directory), images are auto-saved to `$GEMINI_IMAGE_OUTPUT_DIR/YYYY-MM/` with a timestamp prefix:

```bash
# -f "sunset.png" → saves to $GEMINI_IMAGE_OUTPUT_DIR/2026-03/2026-03-01-14-30-00-sunset.png
uv run <skill_dir>/scripts/generate_image.py -p "a sunset" -f "sunset.png"

# -f "/custom/path/sunset.png" → saves to /custom/path/2026-03-01-14-30-00-sunset.png
uv run <skill_dir>/scripts/generate_image.py -p "a sunset" -f "/custom/path/sunset.png"
```

## Configuration

Environment variables (auto-injected via OpenClaw `env.vars`):

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Gemini API key |
| `GEMINI_BASE_URL` | No | Custom API endpoint URL (for alternative deployments) |
| `GEMINI_IMAGE_MODEL` | No | Model ID override (default: `gemini-3.1-flash-image`) |
| `GEMINI_IMAGE_OUTPUT_DIR` | No | Output directory for generated images (default: `~/.openclaw/workspace/images`) |

## Prompt Writing

For prompt templates, examples, and best practices, see [references/prompting.md](references/prompting.md).

Key principle: **describe the scene as a narrative paragraph**, not a keyword list. Include subject, environment, lighting, mood, and camera perspective. The more specific and descriptive, the better the result.

## Model Capabilities

- **World knowledge**: renders real-world subjects accurately
- **Text rendering**: generates legible text in images, suitable for mockups and cards
- **Character consistency**: maintains appearance across a workflow (up to 5 characters, 14 objects)
- **Infographics**: diagrams, flowcharts, data visualizations from descriptions
- **Production range**: 512px to 4K, 10 aspect ratios

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `No API key provided` | `GEMINI_API_KEY` not set | Set env var or use `-k` |
| `Too many input images (N)` | More than 14 `-i` args | Reduce to ≤14 images |
| `Error loading input image` | File not found or corrupt | Check path and file integrity |
| `No image was generated` | API returned text-only response | Rephrase prompt; some prompts trigger safety filters |
| First run slow (~10s) | `uv` downloading dependencies | Subsequent runs use cache, ~1s startup |
