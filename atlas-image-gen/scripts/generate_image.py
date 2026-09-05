#!/usr/bin/env python3
"""Generate images through Atlas Cloud with one guarded submission."""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


DEFAULT_API_BASE = "https://api.atlascloud.ai"
DEFAULT_MODEL = "black-forest-labs/flux-schnell"
DEFAULT_OUTPUT_DIR = os.path.join(os.path.expanduser("~"), ".openclaw", "workspace", "images")
USER_AGENT = "atlas-image-gen/0.1.0"
TERMINAL_SUCCESS = {"completed", "succeeded", "success"}
TERMINAL_FAILURE = {"cancelled", "canceled", "failed", "error"}
RETRYABLE_HTTP_CODES = {408, 409, 425, 429, 500, 502, 503, 504}
MAX_GET_ATTEMPTS = 3

OpenUrl = Callable[..., Any]


class AtlasError(RuntimeError):
    """A user-facing Atlas API or output error."""


def _http_error_text(exc: urllib.error.HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8", errors="replace")
    except Exception:
        body = ""
    return f"HTTP {exc.code}" + (f": {body[:500]}" if body else "")


def _decode_json_response(response: Any) -> dict[str, Any]:
    raw = response.read().decode("utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise AtlasError("Atlas Cloud returned a non-object JSON response")
    return data


def submit_generation(
    *,
    api_base: str,
    api_key: str,
    payload: dict[str, Any],
    open_url: OpenUrl = urllib.request.urlopen,
) -> dict[str, Any]:
    """Submit one generation request. This function intentionally has no retry loop."""
    url = f"{api_base.rstrip('/')}/api/v1/model/generateImage"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with open_url(request, timeout=60) as response:
            return _decode_json_response(response)
    except urllib.error.HTTPError as exc:
        raise AtlasError(f"Generation submission failed ({_http_error_text(exc)}); POST was not retried") from exc
    except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
        raise AtlasError(f"Generation submission failed ({exc}); POST was not retried") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise AtlasError(f"Generation submission returned invalid JSON; POST was not retried: {exc}") from exc


def _get_json_with_retry(
    url: str,
    *,
    api_key: str,
    open_url: OpenUrl = urllib.request.urlopen,
    sleep: Callable[[float], None] = time.sleep,
    attempts: int = MAX_GET_ATTEMPTS,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(attempts):
        request = urllib.request.Request(
            url,
            method="GET",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
        )
        try:
            with open_url(request, timeout=30) as response:
                return _decode_json_response(response)
        except urllib.error.HTTPError as exc:
            if exc.code not in RETRYABLE_HTTP_CODES:
                raise AtlasError(f"Prediction lookup failed ({_http_error_text(exc)})") from exc
            last_error = exc
        except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
            last_error = exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise AtlasError(f"Prediction lookup returned invalid JSON: {exc}") from exc

        if attempt + 1 < attempts:
            sleep(min(2**attempt, 4))

    raise AtlasError(f"Prediction lookup failed after {attempts} GET attempts: {last_error}")


def _unwrap(data: dict[str, Any]) -> dict[str, Any]:
    nested = data.get("data")
    return nested if isinstance(nested, dict) else data


def prediction_id(data: dict[str, Any]) -> str:
    value = _unwrap(data).get("id") or _unwrap(data).get("request_id")
    if not isinstance(value, str) or not value:
        raise AtlasError("Generation response did not include a prediction id")
    return value


def prediction_url(api_base: str, data: dict[str, Any], request_id: str) -> str:
    item = _unwrap(data)
    urls = item.get("urls")
    if isinstance(urls, dict) and isinstance(urls.get("result"), str):
        candidate = urls["result"]
    else:
        candidate = f"{api_base.rstrip('/')}/api/v1/model/prediction/{urllib.parse.quote(request_id, safe='')}"
    parsed = urllib.parse.urlparse(candidate)
    if parsed.scheme != "https" or not parsed.netloc:
        raise AtlasError("Prediction result URL must use HTTPS")
    api_host = urllib.parse.urlparse(api_base).netloc.lower()
    if parsed.netloc.lower() != api_host:
        raise AtlasError("Prediction result URL must use the configured Atlas Cloud API host")
    return candidate


def _status(data: dict[str, Any]) -> str:
    value = _unwrap(data).get("status", "")
    return str(value).strip().lower()


def output_urls(data: dict[str, Any]) -> list[str]:
    item = _unwrap(data)
    raw = item.get("outputs", item.get("output", []))
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    urls: list[str] = []
    for value in raw:
        if not isinstance(value, str):
            continue
        parsed = urllib.parse.urlparse(value)
        if parsed.scheme == "https" and parsed.netloc:
            urls.append(value)
    return urls


def wait_for_prediction(
    initial: dict[str, Any],
    *,
    api_base: str,
    api_key: str,
    poll_interval: float,
    timeout: float,
    open_url: OpenUrl = urllib.request.urlopen,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    request_id = prediction_id(initial)
    url = prediction_url(api_base, initial, request_id)
    current = initial
    deadline = monotonic() + timeout

    while True:
        status = _status(current)
        if status in TERMINAL_SUCCESS:
            return current
        if status in TERMINAL_FAILURE:
            item = _unwrap(current)
            detail = item.get("error") or item.get("logs") or "unknown error"
            raise AtlasError(f"Prediction failed: {detail}")
        if monotonic() >= deadline:
            raise AtlasError(f"Timed out waiting for prediction {request_id}")
        sleep(poll_interval)
        current = _get_json_with_retry(url, api_key=api_key, open_url=open_url, sleep=sleep)


def _get_bytes_with_retry(
    url: str,
    *,
    open_url: OpenUrl = urllib.request.urlopen,
    sleep: Callable[[float], None] = time.sleep,
) -> bytes:
    last_error: Exception | None = None
    for attempt in range(MAX_GET_ATTEMPTS):
        request = urllib.request.Request(
            url,
            method="GET",
            headers={"Accept": "image/*", "User-Agent": USER_AGENT},
        )
        try:
            with open_url(request, timeout=60) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code not in RETRYABLE_HTTP_CODES:
                raise AtlasError(f"Image download failed ({_http_error_text(exc)})") from exc
            last_error = exc
        except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
            last_error = exc
        if attempt + 1 < MAX_GET_ATTEMPTS:
            sleep(min(2**attempt, 4))
    raise AtlasError(f"Image download failed after {MAX_GET_ATTEMPTS} GET attempts: {last_error}")


def image_extension(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    raise AtlasError("Downloaded output is not a recognized PNG, JPEG, GIF, or WebP image")


def resolve_output_path(filename: str, *, index: int, total: int, extension: str) -> Path:
    now = datetime.now()
    raw = Path(filename)
    stem = raw.stem if raw.suffix else raw.name
    if total > 1:
        stem = f"{stem}-{index}"
    if not re.match(r"^\d{4}-\d{2}-\d{2}", stem):
        stem = f"{now:%Y-%m-%d-%H-%M-%S}-{stem}"
    name = stem + extension
    if raw.parent == Path("."):
        root = Path(os.environ.get("ATLASCLOUD_IMAGE_OUTPUT_DIR", DEFAULT_OUTPUT_DIR))
        return root / f"{now:%Y-%m}" / name
    return raw.parent / name


def download_outputs(
    urls: list[str],
    *,
    filename: str,
    open_url: OpenUrl = urllib.request.urlopen,
    sleep: Callable[[float], None] = time.sleep,
) -> list[Path]:
    paths: list[Path] = []
    for index, url in enumerate(urls, start=1):
        data = _get_bytes_with_retry(url, open_url=open_url, sleep=sleep)
        path = resolve_output_path(
            filename,
            index=index,
            total=len(urls),
            extension=image_extension(data),
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        paths.append(path.resolve())
    return paths


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate images through Atlas Cloud")
    parser.add_argument("--prompt", "-p", required=True, help="Image description")
    parser.add_argument("--filename", "-f", required=True, help="Output filename")
    parser.add_argument("--count", "-n", type=int, choices=range(1, 5), default=1)
    parser.add_argument("--size", default="1024x1024", help="Output size as WIDTHxHEIGHT")
    parser.add_argument("--seed", type=int, default=-1)
    parser.add_argument("--model", "-m", default=os.environ.get("ATLASCLOUD_IMAGE_MODEL", DEFAULT_MODEL))
    parser.add_argument("--poll-interval", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=300.0)
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[1-9]\d{1,4}x[1-9]\d{1,4}", args.size):
        parser.error("--size must use WIDTHxHEIGHT, for example 1024x1024")
    if args.poll_interval < 0:
        parser.error("--poll-interval must be non-negative")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    api_key = os.environ.get("ATLASCLOUD_API_KEY", "")
    if not api_key:
        print("Error: ATLASCLOUD_API_KEY is not set", file=sys.stderr)
        return 2
    api_base = os.environ.get("ATLASCLOUD_API_BASE_URL", DEFAULT_API_BASE)
    if urllib.parse.urlparse(api_base).scheme != "https":
        print("Error: ATLASCLOUD_API_BASE_URL must use HTTPS", file=sys.stderr)
        return 2

    payload = {
        "model": args.model,
        "prompt": args.prompt,
        "size": args.size.replace("x", "*"),
        "num_images": args.count,
        "seed": args.seed,
    }
    try:
        initial = submit_generation(api_base=api_base, api_key=api_key, payload=payload)
        completed = wait_for_prediction(
            initial,
            api_base=api_base,
            api_key=api_key,
            poll_interval=args.poll_interval,
            timeout=args.timeout,
        )
        urls = output_urls(completed)
        if not urls:
            raise AtlasError("Prediction succeeded but returned no HTTPS image outputs")
        paths = download_outputs(urls, filename=args.filename)
    except AtlasError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    for path in paths:
        print(f"Image saved: {path}")
        print(f"MEDIA: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
