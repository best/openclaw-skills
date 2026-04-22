#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "openai>=1.75.0",
# ]
# ///
"""Generate or edit images with the OpenAI Image API.

Defaults to gpt-image-2 and supports provider fallback via a small JSON config.
Designed for cases where the host application's built-in image tool lags behind
new OpenAI image model rollouts.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import sys
import urllib.request
import subprocess
from contextlib import ExitStack
from pathlib import Path

from openai import OpenAI

DEFAULT_MODEL = "gpt-image-2"
DEFAULT_OUTPUT_DIR = os.path.join(os.path.expanduser("~"), ".openclaw", "workspace", "images")
DEFAULT_OUTPUT_FORMAT = "png"
# Supported by gpt-image-2 (OpenAI, 2025-04+)
# 1K: 1024×1024 (square, default)
# Wide: 1536×1024, 2048×1152
# Tall: 1024×1536, 2160×3840
# 2K: 2048×2048
# 4K: 3840×2160
VALID_SIZES = [
    "auto",
    # 1K / legacy
    "1024x1024",
    "1536x1024",
    "1024x1536",
    # 2K / 4K (gpt-image-2 extended)
    "2048x2048",
    "2048x1152",
    "3840x2160",
    "2160x3840",
]
VALID_OUTPUT_FORMATS = ["png", "webp", "jpeg"]
VALID_QUALITIES = ["auto", "low", "medium", "high"]
VALID_BACKGROUNDS = ["auto", "transparent", "opaque"]
VALID_MODERATION = ["auto", "low"]
VALID_INPUT_FIDELITY = ["low", "high"]
RETRYABLE_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}
MAX_INPUT_IMAGES = 16


def load_providers(config_path: str | None = None) -> list[dict]:
    """Load provider chain from JSON config or single-provider env vars."""
    paths = [config_path, os.environ.get("OPENAI_IMAGE_CONFIG")]
    for raw in filter(None, paths):
        if os.path.isfile(raw):
            with open(raw, encoding="utf-8") as f:
                data = json.load(f)
            providers = data.get("providers", [])
            if providers:
                return providers

    api_key_env = "OPENAI_IMAGE_API_KEY"
    if not os.environ.get(api_key_env):
        return []

    return [{
        "name": "default",
        "base_url": os.environ.get("OPENAI_IMAGE_BASE_URL"),
        "api_key_env": api_key_env,
        "model": os.environ.get("OPENAI_IMAGE_MODEL", DEFAULT_MODEL),
    }]


def classify_error(exc: Exception) -> str:
    status = getattr(exc, "status_code", None)
    response = getattr(exc, "response", None)
    if status is None and response is not None:
        status = getattr(response, "status_code", None)

    if status in {401, 403}:
        return "auth"
    if status in RETRYABLE_STATUS_CODES:
        return "retryable"

    text = str(exc).lower()
    if any(token in text for token in ["timeout", "timed out", "connection", "temporarily unavailable", "overloaded", "capacity"]):
        return "retryable"
    return "fatal"


def workspace_display_path(path: Path) -> Path:
    """Return a workspace-accessible path if a symlinked images dir is in use."""
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


def normalize_extension(output_format: str) -> str:
    return ".jpg" if output_format == "jpeg" else f".{output_format}"


def resolve_output_path(filename: str, output_format: str, index: int | None = None) -> Path:
    """Resolve output path. Plain filename -> output_dir/YYYY-MM/timestamp-name.ext."""
    from datetime import datetime

    now = datetime.now()
    raw = Path(filename)
    ext = normalize_extension(output_format)

    stem = raw.stem if raw.suffix else raw.name
    if index is not None:
        stem = f"{stem}-{index}"

    if not re.match(r"^\d{4}-\d{2}-\d{2}", stem):
        stem = now.strftime("%Y-%m-%d-%H-%M-%S-") + stem

    final_name = stem + ext

    if raw.parent == Path("."):
        output_dir = os.environ.get("OPENAI_IMAGE_OUTPUT_DIR", DEFAULT_OUTPUT_DIR)
        month_dir = now.strftime("%Y-%m")
        return Path(output_dir) / month_dir / final_name
    return raw.parent / final_name


def maybe_fetch_image_bytes(entry) -> bytes | None:
    if getattr(entry, "b64_json", None):
        return base64.b64decode(entry.b64_json)
    if getattr(entry, "url", None):
        request = urllib.request.Request(
            entry.url,
            headers={
                "User-Agent": "curl/8.0.0",
                "Accept": "image/*,*/*;q=0.8",
            },
        )
        try:
            with urllib.request.urlopen(request) as resp:
                return resp.read()
        except Exception:
            try:
                result = subprocess.run(
                    ["curl", "-fsSL", entry.url],
                    check=True,
                    capture_output=True,
                )
                return result.stdout
            except Exception:
                raise
    return None


def build_client(api_key: str, base_url: str | None = None) -> OpenAI:
    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def generate_with_fallback(
    providers: list[dict],
    *,
    prompt: str,
    images: list[str],
    mask: str | None,
    model_override: str | None,
    api_key_override: str | None,
    base_url_override: str | None,
    size: str | None,
    quality: str | None,
    background: str | None,
    output_format: str | None,
    output_compression: int | None,
    moderation: str | None,
    input_fidelity: str | None,
    count: int,
) -> tuple[object, str, str]:
    """Try providers in order, falling back on retryable/auth failures."""

    def call_single(client: OpenAI, model: str):
        kwargs = {
            "model": model,
            "prompt": prompt,
            "n": count,
        }
        if size is not None:
            kwargs["size"] = size
        if quality is not None:
            kwargs["quality"] = quality
        if background is not None:
            kwargs["background"] = background
        if output_format is not None:
            kwargs["output_format"] = output_format
        if output_compression is not None:
            kwargs["output_compression"] = output_compression

        if images:
            if input_fidelity is not None:
                kwargs["input_fidelity"] = input_fidelity
            with ExitStack() as stack:
                opened_images = [stack.enter_context(open(path, "rb")) for path in images]
                kwargs["image"] = opened_images if len(opened_images) > 1 else opened_images[0]
                if mask is not None:
                    kwargs["mask"] = stack.enter_context(open(mask, "rb"))
                return client.images.edit(**kwargs)

        if moderation is not None:
            kwargs["moderation"] = moderation
        return client.images.generate(**kwargs)

    # CLI override -> single-provider mode
    if api_key_override or base_url_override:
        api_key = api_key_override or os.environ.get("OPENAI_IMAGE_API_KEY")
        if not api_key:
            print("Error: --api-key not provided and OPENAI_IMAGE_API_KEY is unset.", file=sys.stderr)
            sys.exit(1)
        base_url = base_url_override or os.environ.get("OPENAI_IMAGE_BASE_URL")
        model = model_override or os.environ.get("OPENAI_IMAGE_MODEL", DEFAULT_MODEL)
        print(f"Using provider: cli-override ({model})")
        if base_url:
            print(f"Using endpoint: {base_url}")
        client = build_client(api_key, base_url)
        return call_single(client, model), "cli-override", model

    last_error: Exception | None = None
    for idx, provider in enumerate(providers):
        name = provider.get("name", f"provider-{idx}")
        api_key_env = provider.get("api_key_env", "")
        api_key = os.environ.get(api_key_env, "")
        if not api_key:
            print(f"Skipping {name}: no API key (env {api_key_env or '?'})")
            continue

        base_url = provider.get("base_url")
        model = model_override or provider.get("model", DEFAULT_MODEL)
        print(f"Trying provider: {name} ({model})" + (f" via {base_url}" if base_url else " (direct)") + "...")
        try:
            client = build_client(api_key, base_url)
            return call_single(client, model), name, model
        except Exception as exc:
            last_error = exc
            kind = classify_error(exc)
            if kind == "auth":
                print(f"Provider {name} failed (auth): {exc}")
                continue
            if kind == "retryable":
                print(f"Provider {name} failed (retryable): {exc}")
                continue
            print(f"Provider {name} failed (non-retryable): {exc}", file=sys.stderr)
            raise

    if last_error is not None:
        print(f"All providers failed. Last error: {last_error}", file=sys.stderr)
        raise last_error
    print("Error: No providers available (check OPENAI_IMAGE_API_KEY or OPENAI_IMAGE_CONFIG).", file=sys.stderr)
    sys.exit(1)


def validate_file(path: str, label: str) -> None:
    if not os.path.isfile(path):
        print(f"Error: {label} not found: {path}", file=sys.stderr)
        sys.exit(1)



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate or edit images with OpenAI Image API")
    parser.add_argument("--prompt", "-p", required=True, help="Image description or edit instruction")
    parser.add_argument("--filename", "-f", required=True, help="Output filename")
    parser.add_argument("--input-image", "-i", action="append", dest="input_images", help="Input image path. Repeatable, up to 16")
    parser.add_argument("--mask", help="Optional PNG mask for edit mode")
    parser.add_argument("--size", choices=VALID_SIZES, default="auto", help="Output size (default: auto)")
    parser.add_argument("--quality", choices=VALID_QUALITIES, default="auto", help="Output quality (default: auto)")
    parser.add_argument("--background", choices=VALID_BACKGROUNDS, default="auto", help="Background mode (default: auto)")
    parser.add_argument("--output-format", choices=VALID_OUTPUT_FORMATS, default=DEFAULT_OUTPUT_FORMAT, help="Output format (default: png)")
    parser.add_argument("--output-compression", type=int, help="Compression 0-100 for webp/jpeg")
    parser.add_argument("--moderation", choices=VALID_MODERATION, default="auto", help="Moderation level for generation mode (default: auto)")
    parser.add_argument("--input-fidelity", choices=VALID_INPUT_FIDELITY, default="low", help="Edit fidelity for input images (default: low)")
    parser.add_argument("--count", "-n", type=int, default=1, help="Number of images to generate (1-10)")
    parser.add_argument("--api-key", "-k", help="Override API key (single-provider mode)")
    parser.add_argument("--base-url", help="Override API endpoint (single-provider mode)")
    parser.add_argument("--model", "-m", help=f"Override model ID (default per provider, usually {DEFAULT_MODEL})")
    parser.add_argument("--config", help="Path to providers.json config file")
    return parser.parse_args()



def main() -> None:
    args = parse_args()

    if args.count < 1 or args.count > 10:
        print("Error: --count must be between 1 and 10.", file=sys.stderr)
        sys.exit(1)
    if args.output_compression is not None and not (0 <= args.output_compression <= 100):
        print("Error: --output-compression must be between 0 and 100.", file=sys.stderr)
        sys.exit(1)
    if args.output_compression is not None and args.output_format not in {"jpeg", "webp"}:
        print("Error: --output-compression only applies to jpeg/webp output.", file=sys.stderr)
        sys.exit(1)
    if args.background == "transparent" and args.output_format not in {"png", "webp"}:
        print("Error: transparent background requires png or webp output.", file=sys.stderr)
        sys.exit(1)

    input_images = args.input_images or []
    if len(input_images) > MAX_INPUT_IMAGES:
        print(f"Error: Too many input images ({len(input_images)}). Maximum is {MAX_INPUT_IMAGES}.", file=sys.stderr)
        sys.exit(1)
    for image in input_images:
        validate_file(image, "input image")
    if args.mask:
        validate_file(args.mask, "mask")
    if args.mask and not input_images:
        print("Error: --mask requires at least one --input-image.", file=sys.stderr)
        sys.exit(1)

    providers = load_providers(args.config)
    if not providers and not args.api_key:
        print("Error: No providers configured and no --api-key provided.", file=sys.stderr)
        print("Create an OPENAI_IMAGE_CONFIG file or set OPENAI_IMAGE_API_KEY.", file=sys.stderr)
        sys.exit(1)

    output_dir = os.environ.get("OPENAI_IMAGE_OUTPUT_DIR", DEFAULT_OUTPUT_DIR)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    mode = "editing" if input_images else "generation"
    print(f"Mode: {mode}")
    print(f"Output: {args.output_format}, size {args.size}, quality {args.quality}, count {args.count}")

    try:
        response, provider_name, model_used = generate_with_fallback(
            providers=providers,
            prompt=args.prompt,
            images=input_images,
            mask=args.mask,
            model_override=args.model,
            api_key_override=args.api_key,
            base_url_override=args.base_url,
            size=args.size,
            quality=args.quality,
            background=args.background,
            output_format=args.output_format,
            output_compression=args.output_compression,
            moderation=args.moderation if not input_images else None,
            input_fidelity=args.input_fidelity if input_images else None,
            count=args.count,
        )
    except Exception as exc:
        print(f"Error generating image: {exc}", file=sys.stderr)
        sys.exit(1)

    items = list(getattr(response, "data", []) or [])
    if not items:
        print("Error: No image returned by API.", file=sys.stderr)
        sys.exit(1)

    saved_paths: list[Path] = []
    for idx, item in enumerate(items, start=1):
        image_bytes = maybe_fetch_image_bytes(item)
        if image_bytes is None:
            continue
        output_path = resolve_output_path(args.filename, args.output_format, idx if len(items) > 1 else None)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_bytes)
        saved_paths.append(output_path)
        revised_prompt = getattr(item, "revised_prompt", None)
        if revised_prompt:
            print(f"Revised prompt [{idx}]: {revised_prompt}")

    if not saved_paths:
        print("Error: API response contained no savable image data.", file=sys.stderr)
        sys.exit(1)

    print("")
    for path in saved_paths:
        display_path = workspace_display_path(path)
        mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        print(f"Saved: {display_path} ({mime}) via {provider_name}/{model_used}")
        print(f"MEDIA: {display_path}")


if __name__ == "__main__":
    main()
