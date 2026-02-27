#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "google-genai>=1.0.0",
#     "pillow>=10.0.0",
# ]
# ///
"""
Generate images using Gemini 3.1 Flash Image (Nano Banana 2) via third-party API proxy.

Supports text-to-image, image editing, multi-image composition, aspect ratio control,
and resolutions from 1K to 4K.

Usage:
    uv run generate_image.py --prompt "your image description" --filename "output.png"
    uv run generate_image.py --prompt "a vertical poster" -f "poster.png" --aspect-ratio 9:16
    uv run generate_image.py --prompt "edit this" -f "out.png" -i input.png --resolution 2K

Multi-image editing (up to 14 images):
    uv run generate_image.py --prompt "combine these images" -f "out.png" -i img1.png -i img2.png
"""

import argparse
import os
import sys
from pathlib import Path


DEFAULT_BASE_URL = "https://api.gptclubapi.xyz/gemini"
DEFAULT_MODEL = "gemini-3.1-flash-image"
VALID_ASPECT_RATIOS = ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]


def get_api_key(provided_key: str | None) -> str | None:
    """Get API key from argument first, then environment."""
    if provided_key:
        return provided_key
    return os.environ.get("GPTCLUB_API_KEY") or os.environ.get("GEMINI_API_KEY")


def get_base_url(provided_url: str | None) -> str:
    """Get base URL from argument or environment."""
    if provided_url:
        return provided_url
    return os.environ.get("GEMINI_BASE_URL", DEFAULT_BASE_URL)


def get_model(provided_model: str | None) -> str:
    """Get model name from argument or environment."""
    if provided_model:
        return provided_model
    return os.environ.get("GEMINI_IMAGE_MODEL", DEFAULT_MODEL)


def main():
    parser = argparse.ArgumentParser(
        description="Generate/edit images using Gemini 3.1 Flash Image (Nano Banana 2) via proxy"
    )
    parser.add_argument(
        "--prompt", "-p",
        required=True,
        help="Image description/prompt"
    )
    parser.add_argument(
        "--filename", "-f",
        required=True,
        help="Output filename (e.g., sunset-mountains.png)"
    )
    parser.add_argument(
        "--input-image", "-i",
        action="append",
        dest="input_images",
        metavar="IMAGE",
        help="Input image path(s) for editing/composition. Can be specified multiple times (up to 14 images)."
    )
    parser.add_argument(
        "--resolution", "-r",
        choices=["1K", "2K", "4K"],
        default="1K",
        help="Output resolution: 1K (default), 2K, or 4K"
    )
    parser.add_argument(
        "--aspect-ratio", "-a",
        choices=VALID_ASPECT_RATIOS,
        default=None,
        dest="aspect_ratio",
        help="Aspect ratio (e.g., 16:9, 9:16, 1:1, 3:2, 4:3, 21:9). Default: model decides."
    )
    parser.add_argument(
        "--api-key", "-k",
        help="API key (overrides GPTCLUB_API_KEY / GEMINI_API_KEY env var)"
    )
    parser.add_argument(
        "--base-url",
        help=f"API proxy base URL (default: {DEFAULT_BASE_URL})"
    )
    parser.add_argument(
        "--model", "-m",
        help=f"Model name (default: {DEFAULT_MODEL})"
    )

    args = parser.parse_args()

    # Get configuration
    api_key = get_api_key(args.api_key)
    if not api_key:
        print("Error: No API key provided.", file=sys.stderr)
        print("Please either:", file=sys.stderr)
        print("  1. Provide --api-key argument", file=sys.stderr)
        print("  2. Set GPTCLUB_API_KEY or GEMINI_API_KEY environment variable", file=sys.stderr)
        sys.exit(1)

    base_url = get_base_url(args.base_url)
    model = get_model(args.model)

    # Import here after checking API key to avoid slow import on error
    from google import genai
    from google.genai import types
    from PIL import Image as PILImage

    # Initialise client with custom proxy endpoint
    client = genai.Client(
        api_key=api_key,
        http_options={"base_url": base_url}
    )
    print(f"Using model: {model}")
    print(f"Using endpoint: {base_url}")

    # Set up output path
    output_path = Path(args.filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load input images if provided (up to 14 supported)
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
                    width, height = copied.size
                input_images.append(copied)
                print(f"Loaded input image: {img_path}")

                # Track largest dimension for auto-resolution
                max_input_dim = max(max_input_dim, width, height)
            except Exception as e:
                print(f"Error loading input image '{img_path}': {e}", file=sys.stderr)
                sys.exit(1)

        # Auto-detect resolution from largest input if not explicitly set
        if args.resolution == "1K" and max_input_dim > 0:  # Default value
            if max_input_dim >= 3000:
                output_resolution = "4K"
            elif max_input_dim >= 1500:
                output_resolution = "2K"
            else:
                output_resolution = "1K"
            print(f"Auto-detected resolution: {output_resolution} (from max input dimension {max_input_dim})")

    # Build contents (images first if editing, prompt only if generating)
    if input_images:
        contents = [*input_images, args.prompt]
        img_count = len(input_images)
        print(f"Processing {img_count} image{'s' if img_count > 1 else ''} with resolution {output_resolution}...")
    else:
        contents = args.prompt
        config_parts = [f"resolution {output_resolution}"]
        if args.aspect_ratio:
            config_parts.append(f"aspect ratio {args.aspect_ratio}")
        print(f"Generating image with {', '.join(config_parts)}...")

    # Build ImageConfig
    image_config_kwargs = {"image_size": output_resolution}
    if args.aspect_ratio:
        image_config_kwargs["aspect_ratio"] = args.aspect_ratio

    try:
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                image_config=types.ImageConfig(**image_config_kwargs)
            )
        )

        # Process response and convert to PNG
        image_saved = False
        for part in response.parts:
            if part.text is not None:
                print(f"Model response: {part.text}")
            elif part.inline_data is not None:
                # Convert inline data to PIL Image and save as PNG
                from io import BytesIO

                image_data = part.inline_data.data
                if isinstance(image_data, str):
                    import base64
                    image_data = base64.b64decode(image_data)

                image = PILImage.open(BytesIO(image_data))

                # Ensure RGB mode for PNG
                if image.mode == 'RGBA':
                    rgb_image = PILImage.new('RGB', image.size, (255, 255, 255))
                    rgb_image.paste(image, mask=image.split()[3])
                    rgb_image.save(str(output_path), 'PNG')
                elif image.mode == 'RGB':
                    image.save(str(output_path), 'PNG')
                else:
                    image.convert('RGB').save(str(output_path), 'PNG')
                image_saved = True

        if image_saved:
            full_path = output_path.resolve()
            print(f"\nImage saved: {full_path}")
            # OpenClaw parses MEDIA tokens and will attach the file on supported providers.
            print(f"MEDIA: {full_path}")
        else:
            print("Error: No image was generated in the response.", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"Error generating image: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
