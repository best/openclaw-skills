#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "google-genai>=1.0.0",
#     "pillow>=10.0.0",
# ]
# ///
"""
Generate images using the Gemini Image Generation API with provider fallback.

Supports text-to-image, image editing, multi-image composition, aspect ratio control,
and resolutions from 1K to 4K. Tries providers in order, falling back on retryable errors.

Usage:
    uv run generate_image.py --prompt "your image description" --filename "output.png"
    uv run generate_image.py --prompt "a vertical poster" -f "poster.png" --aspect-ratio 9:16
    uv run generate_image.py --prompt "edit this" -f "out.png" -i input.png --resolution 2K
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


DEFAULT_MODEL = "gemini-3.1-flash-image"
DEFAULT_OUTPUT_DIR = os.path.join(os.path.expanduser("~"), ".openclaw", "workspace", "images")
VALID_ASPECT_RATIOS = ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]

# HTTP status codes that trigger fallback to next provider
RETRYABLE_STATUS_CODES = {429, 500, 502, 503}


def load_providers(config_path: str | None = None) -> list[dict]:
    """Load provider chain from GEMINI_IMAGE_CONFIG or an explicit config path."""
    raw = config_path or os.environ.get("GEMINI_IMAGE_CONFIG")
    if not raw:
        print("Error: GEMINI_IMAGE_CONFIG is not set and --config was not provided.", file=sys.stderr)
        return []
    if not os.path.isfile(raw):
        print(f"Error: provider config not found: {raw}", file=sys.stderr)
        return []

    with open(raw, encoding="utf-8") as f:
        data = json.load(f)
    providers = data.get("providers", [])
    if not isinstance(providers, list) or not providers:
        print(f"Error: provider config contains no providers: {raw}", file=sys.stderr)
        return []
    return providers


def is_retryable_error(error: Exception) -> bool:
    """Check if an error is retryable (should fall back to next provider)."""
    err_str = str(error).lower()
    # Check for HTTP status codes
    for code in RETRYABLE_STATUS_CODES:
        if str(code) in err_str:
            return True
    # Check for connection/timeout errors
    retryable_keywords = ["timeout", "connection", "unavailable", "overloaded", "capacity"]
    return any(kw in err_str for kw in retryable_keywords)


def workspace_display_path(path: Path) -> Path:
    """Return a workspace-accessible path if the real path is reachable via a workspace symlink."""
    workspace_images = Path(DEFAULT_OUTPUT_DIR)
    if workspace_images.is_symlink():
        try:
            real_target = workspace_images.resolve()
            real_path = path.resolve()
            if real_path == real_target or str(real_path).startswith(str(real_target) + os.sep):
                rel = real_path.relative_to(real_target)
                return workspace_images / rel
        except (ValueError, OSError):
            pass
    return Path(os.path.abspath(str(path)))


def resolve_output_path(filename: str) -> Path:
    """Resolve output path. Pure filename → output_dir/YYYY-MM/timestamp-filename."""
    from datetime import datetime
    p = Path(filename)
    now = datetime.now()

    name = p.name
    if not re.match(r"^\d{4}-\d{2}-\d{2}", name):
        name = now.strftime("%Y-%m-%d-%H-%M-%S-") + name

    if p.parent == Path("."):
        output_dir = os.environ.get("GEMINI_IMAGE_OUTPUT_DIR", DEFAULT_OUTPUT_DIR)
        month_dir = now.strftime("%Y-%m")
        return Path(output_dir) / month_dir / name
    else:
        return p.parent / name


def generate_image(client, model: str, contents, image_config_kwargs: dict):
    """Call the Gemini API to generate an image. Returns response object."""
    from google.genai import types
    return client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
            image_config=types.ImageConfig(**image_config_kwargs),
        ),
    )


def generate_with_fallback(
    providers: list[dict],
    contents,
    image_config_kwargs: dict,
    model_override: str | None = None,
) -> tuple:
    """Try providers in order, falling back on retryable errors.

    Returns (response, provider_name, model_used).
    """
    from google import genai

    # Provider chain mode
    last_error = None
    for i, provider in enumerate(providers):
        name = provider.get("name", f"provider-{i}")
        api_key = provider.get("api_key", "")
        if not api_key:
            api_key_env = provider.get("api_key_env", "")
            if api_key_env:
                api_key = os.environ.get(api_key_env, "")
            if not api_key:
                source = f"env {api_key_env}" if api_key_env else "api_key/api_key_env"
                print(f"Skipping {name}: no API key ({source})")
                continue

        base_url = provider.get("base_url")
        model = model_override or provider.get("model", DEFAULT_MODEL)

        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["http_options"] = {"base_url": base_url}

        print(f"Trying provider: {name} ({model})" + (f" via {base_url}" if base_url else " (direct)") + "...")

        try:
            client = genai.Client(**client_kwargs)
            resp = generate_image(client, model, contents, image_config_kwargs)
            return resp, name, model
        except Exception as e:
            last_error = e
            if is_retryable_error(e):
                print(f"Provider {name} failed (retryable): {e}")
                continue
            else:
                print(f"Provider {name} failed (non-retryable): {e}", file=sys.stderr)
                raise

    if last_error:
        print(f"All providers failed. Last error: {last_error}", file=sys.stderr)
        raise last_error
    print("Error: No providers available (check GEMINI_IMAGE_CONFIG provider api_key/api_key_env values).", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Generate/edit images using the Gemini Image Generation API"
    )
    parser.add_argument("--prompt", "-p", required=True, help="Image description/prompt")
    parser.add_argument("--filename", "-f", required=True, help="Output filename")
    parser.add_argument(
        "--input-image", "-i", action="append", dest="input_images", metavar="IMAGE",
        help="Input image path(s) for editing/composition (up to 14)",
    )
    parser.add_argument("--resolution", "-r", choices=["1K", "2K", "4K"], default="1K",
                        help="Output resolution (default: 1K)")
    parser.add_argument("--aspect-ratio", "-a", choices=VALID_ASPECT_RATIOS, default=None,
                        dest="aspect_ratio", help="Aspect ratio (default: model decides)")
    parser.add_argument("--model", "-m", help=f"Override model ID (default per provider)")
    parser.add_argument("--config", help="Path to providers.json config file")

    args = parser.parse_args()

    # Load provider chain
    providers = load_providers(args.config)
    if not providers:
        print("Create a GEMINI_IMAGE_CONFIG file or pass --config with provider entries containing api_key or api_key_env.", file=sys.stderr)
        sys.exit(1)

    # Import heavy deps
    from PIL import Image as PILImage

    # Resolve output path
    output_path = resolve_output_path(args.filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load input images
    input_images = []
    output_resolution = args.resolution
    if args.input_images:
        if len(args.input_images) > 14:
            print(f"Error: Too many input images ({len(args.input_images)}). Maximum is 14.", file=sys.stderr)
            sys.exit(1)
        max_input_dim = 0
        for img_path in args.input_images:
            try:
                with PILImage.open(img_path) as img:
                    copied = img.copy()
                    w, h = copied.size
                input_images.append(copied)
                print(f"Loaded input image: {img_path}")
                max_input_dim = max(max_input_dim, w, h)
            except Exception as e:
                print(f"Error loading input image '{img_path}': {e}", file=sys.stderr)
                sys.exit(1)
        if args.resolution == "1K" and max_input_dim > 0:
            if max_input_dim >= 3000:
                output_resolution = "4K"
            elif max_input_dim >= 1500:
                output_resolution = "2K"
            print(f"Auto-detected resolution: {output_resolution} (max dim {max_input_dim})")

    # Build contents
    if input_images:
        contents = [*input_images, args.prompt]
        print(f"Processing {len(input_images)} image(s) with resolution {output_resolution}...")
    else:
        contents = args.prompt
        parts = [f"resolution {output_resolution}"]
        if args.aspect_ratio:
            parts.append(f"aspect ratio {args.aspect_ratio}")
        print(f"Generating image with {', '.join(parts)}...")

    # Build image config
    image_config_kwargs = {"image_size": output_resolution}
    if args.aspect_ratio:
        image_config_kwargs["aspect_ratio"] = args.aspect_ratio

    # Generate with fallback
    try:
        response, provider_name, model_used = generate_with_fallback(
            providers=providers,
            contents=contents,
            image_config_kwargs=image_config_kwargs,
            model_override=args.model,
        )
    except Exception as e:
        print(f"Error generating image: {e}", file=sys.stderr)
        sys.exit(1)

    # Save image
    image_saved = False
    for part in response.parts:
        if part.text is not None:
            print(f"Model response: {part.text}")
        elif part.inline_data is not None:
            from io import BytesIO
            image_data = part.inline_data.data
            if isinstance(image_data, str):
                import base64
                image_data = base64.b64decode(image_data)
            image = PILImage.open(BytesIO(image_data))
            if image.mode == "RGBA":
                rgb = PILImage.new("RGB", image.size, (255, 255, 255))
                rgb.paste(image, mask=image.split()[3])
                rgb.save(str(output_path), "PNG")
            elif image.mode == "RGB":
                image.save(str(output_path), "PNG")
            else:
                image.convert("RGB").save(str(output_path), "PNG")
            image_saved = True

    if image_saved:
        display_path = workspace_display_path(output_path)
        print(f"\nImage saved: {display_path} (via {provider_name})")
        print(f"MEDIA: {display_path}")
    else:
        print("Error: No image was generated in the response.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
