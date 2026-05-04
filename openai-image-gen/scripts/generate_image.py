#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "openai>=1.75.0",
# ]
# ///
"""Generate or edit images with the OpenAI Image API.

Defaults to gpt-image-2 and requires provider fallback via a small JSON config.
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
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    """Load provider chain from OPENAI_IMAGE_CONFIG or an explicit config path."""
    raw = config_path or os.environ.get("OPENAI_IMAGE_CONFIG")
    if not raw:
        print("Error: OPENAI_IMAGE_CONFIG is not set and --config was not provided.", file=sys.stderr)
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


def _decode_b64_fallback(raw: str) -> bytes | None:
    """Decode a base64 string with multiple format tolerances.

    Handles:
      - Standard bare base64 (OpenAI native)
      - Data URI with prefix: data:image/png;base64,<b64>  (NewAPI / OneAPI)
      - Whitespace-padded or newline-contaminated payloads
    Returns None on any failure so the caller can try the next source.
    """
    if not raw or not isinstance(raw, str):
        return None
    # Strip data URI prefix if present
    cleaned = raw.strip()
    if cleaned.startswith("data:"):
        cleaned = cleaned.split(",", 1)[-1].strip()
    # Remove internal whitespace/newlines some providers inject
    cleaned = re.sub(r"\s+", "", cleaned)
    # Validate it looks like base64 before attempting decode
    if not re.match(r"^[A-Za-z0-9+/=]+$", cleaned) or len(cleaned) < 100:
        return None
    try:
        return base64.b64decode(cleaned, validate=True)
    except Exception:
        # Some providers use non-standard padding; try with padding fix
        padded = cleaned + "=" * (-len(cleaned) % 4)
        try:
            return base64.b64decode(padded, validate=True)
        except Exception:
            return None


def _fetch_url_fallback(url: str) -> bytes | None:
    """Fetch image bytes from a URL with multiple transport fallbacks.

    Tries: urllib → curl subprocess.
    Returns None on any failure.
    """
    if not url or not isinstance(url, str):
        return None
    headers = {"User-Agent": "curl/8.0.0", "Accept": "image/*,*/*;q=0.8"}
    # Try urllib first
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            if data and len(data) > 100:
                return data
    except Exception:
        pass
    # Fallback to curl
    try:
        result = subprocess.run(
            ["curl", "-fsSL", "--max-time", "30", url],
            check=True,
            capture_output=True,
        )
        if result.stdout and len(result.stdout) > 100:
            return result.stdout
    except Exception:
        pass
    return None


def maybe_fetch_image_bytes(entry) -> bytes | None:
    """Extract image bytes from an API response entry with multi-format auto-detection.

    Strategy (ordered by reliability):
      1. b64_json — inline base64 (handles data URI prefix, padding, whitespace)
      2. url          — remote URL fetch (urllib → curl fallback)
      3. Cross-fallback: if b64_json exists but fails to decode, try url anyway
    """
    sources_tried: list[str] = []

    # Source 1: b64_json (inline base64)
    b64_val = getattr(entry, "b64_json", None)
    if b64_val:
        sources_tried.append("b64_json")
        result = _decode_b64_fallback(b64_val)
        if result is not None:
            return result
        print(f"Warning: b64_json present but failed to decode ({len(str(b64_val))} chars), trying url fallback", file=sys.stderr)

    # Source 2: url (remote fetch)
    url_val = getattr(entry, "url", None)
    if url_val:
        sources_tried.append("url")
        result = _fetch_url_fallback(url_val)
        if result is not None:
            return result

    # Source 3: cross-fallback — we had b64_json but it failed, and we haven't tried url yet
    if "b64_json" in sources_tried and "url" not in sources_tried:
        # No url field available either
        pass

    if sources_tried:
        print(f"Warning: All image extraction sources exhausted (tried: {', '.join(sources_tried)})", file=sys.stderr)
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

    last_error: Exception | None = None
    for idx, provider in enumerate(providers):
        name = provider.get("name", f"provider-{idx}")
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
    print("Error: No providers available (check OPENAI_IMAGE_CONFIG provider api_key/api_key_env values).", file=sys.stderr)
    sys.exit(1)


def validate_file(path: str, label: str) -> None:
    if not os.path.isfile(path):
        print(f"Error: {label} not found: {path}", file=sys.stderr)
        sys.exit(1)



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate or edit images with OpenAI Image API")
    parser.add_argument("--prompt", "-p", required=True, action="append", dest="prompts", help="Image description or edit instruction. Repeat for parallel multi-prompt generation.")
    parser.add_argument("--filename", "-f", required=True, help="Output filename (base name; auto-suffixed for parallel runs)")
    parser.add_argument("--input-image", "-i", action="append", dest="input_images", help="Input image path. Repeatable, up to 16")
    parser.add_argument("--mask", help="Optional PNG mask for edit mode")
    parser.add_argument("--size", choices=VALID_SIZES, default="auto", help="Output size (default: auto)")
    parser.add_argument("--quality", choices=VALID_QUALITIES, default="auto", help="Output quality (default: auto)")
    parser.add_argument("--background", choices=VALID_BACKGROUNDS, default="auto", help="Background mode (default: auto)")
    parser.add_argument("--output-format", choices=VALID_OUTPUT_FORMATS, default=DEFAULT_OUTPUT_FORMAT, help="Output format (default: png)")
    parser.add_argument("--output-compression", type=int, help="Compression 0-100 for webp/jpeg")
    parser.add_argument("--moderation", choices=VALID_MODERATION, default="auto", help="Moderation level for generation mode (default: auto)")
    parser.add_argument("--input-fidelity", choices=VALID_INPUT_FIDELITY, default="low", help="Edit fidelity for input images (default: low)")
    parser.add_argument("--count", "-n", type=int, default=1, help="Number of images to generate per prompt (1-10)")
    parser.add_argument("--parallel", "-j", type=int, default=0, help="Max concurrent API calls for multi-prompt mode (default: auto = number of prompts)")
    parser.add_argument("--model", "-m", help=f"Override model ID (default per provider, usually {DEFAULT_MODEL})")
    parser.add_argument("--config", help="Path to providers.json config file")
    return parser.parse_args()



def _run_single_generation(
    prompt_idx: int,
    prompt: str,
    providers: list[dict],
    args: argparse.Namespace,
) -> tuple[int, list[Path], str, str]:
    """Run a single generation call. Returns (idx, saved_paths, provider_name, model_used)."""
    try:
        response, provider_name, model_used = generate_with_fallback(
            providers=providers,
            prompt=prompt,
            images=args.input_images or [],
            mask=args.mask,
            model_override=args.model,
            size=args.size,
            quality=args.quality,
            background=args.background,
            output_format=args.output_format,
            output_compression=args.output_compression,
            moderation=args.moderation if not (args.input_images or []) else None,
            input_fidelity=args.input_fidelity if (args.input_images or []) else None,
            count=args.count,
        )
        items = list(getattr(response, "data", []) or [])
        if not items:
            print(f"  [prompt {prompt_idx}] No image returned.", file=sys.stderr)
            return (prompt_idx, [], provider_name, model_used)

        saved_paths: list[Path] = []
        for idx, item in enumerate(items, start=1):
            image_bytes = maybe_fetch_image_bytes(item)
            if image_bytes is None:
                continue
            # For multi-prompt: use prompt_idx as suffix; for single-prompt multi-count: use item idx
            total_prompts = len(args.prompts)
            if total_prompts > 1 and args.count == 1:
                out_idx = prompt_idx + 1  # 1-based: v1, v2, v3...
            elif total_prompts > 1:
                out_idx = (prompt_idx * 100) + idx  # p1-1, p1-2, p2-1...
            elif len(items) > 1:
                out_idx = idx
            else:
                out_idx = None
            output_path = resolve_output_path(args.filename, args.output_format, out_idx)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(image_bytes)
            saved_paths.append(output_path)
            revised_prompt = getattr(item, "revised_prompt", None)
            if revised_prompt:
                print(f"  Revised prompt [{prompt_idx}-{idx}]: {revised_prompt}")

        return (prompt_idx, saved_paths, provider_name, model_used)
    except Exception as exc:
        print(f"  [prompt {prompt_idx}] Error: {exc}", file=sys.stderr)
        return (prompt_idx, [], "", "")


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

    prompts = args.prompts

    providers = load_providers(args.config)
    if not providers:
        print("Create an OPENAI_IMAGE_CONFIG file or pass --config with provider entries containing api_key or api_key_env.", file=sys.stderr)
        sys.exit(1)

    output_dir = os.environ.get("OPENAI_IMAGE_OUTPUT_DIR", DEFAULT_OUTPUT_DIR)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    if len(prompts) > 1:
        # Multi-prompt parallel mode
        max_workers = args.parallel if args.parallel > 0 else min(len(prompts), 5)
        print(f"Mode: multi-prompt parallel ({len(prompts)} prompts, {max_workers} workers)")
        print(f"Output: {args.output_format}, size {args.size}, quality {args.quality}, count per prompt: {args.count}")
        print("")

        all_saved: list[tuple[int, Path, str, str]] = []  # (prompt_idx, path, provider, model)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_run_single_generation, i, p, providers, args): i
                for i, p in enumerate(prompts)
            }
            for future in as_completed(futures):
                idx = futures[future]
                result = future.result()
                pidx, paths, prov, mdl = result
                for path in paths:
                    all_saved.append((pidx, path, prov, mdl))

        if not all_saved:
            print("Error: No images generated across all prompts.", file=sys.stderr)
            sys.exit(1)

        # Sort by prompt_idx for stable output order
        all_saved.sort(key=lambda x: x[0])
        print("")
        for pidx, path, prov, mdl in all_saved:
            display_path = workspace_display_path(path)
            mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
            print(f"Saved: {display_path} ({mime}) via {prov}/{mdl}")
            print(f"MEDIA: {display_path}")
        return

    # Single-prompt mode (original behavior)
    prompt = prompts[0]

    mode = "editing" if input_images else "generation"
    print(f"Mode: {mode}")
    print(f"Output: {args.output_format}, size {args.size}, quality {args.quality}, count {args.count}")

    try:
        response, provider_name, model_used = generate_with_fallback(
            providers=providers,
            prompt=prompt,
            images=input_images,
            mask=args.mask,
            model_override=args.model,
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
