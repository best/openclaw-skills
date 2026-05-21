#!/usr/bin/env python3
"""
Extract metadata for AI Feed posts created after the last broadcast time.

The script reads Markdown frontmatter as data only. It never executes article
files or content.
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


DEFAULT_STATE = {"lastBroadcastAt": "1970-01-01T00:00:00Z"}


def load_state(path: Path) -> dict:
    if not path.exists():
        return dict(DEFAULT_STATE)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid state JSON: {exc}")
    if not isinstance(value, dict):
        raise ValueError("state file must contain a JSON object")
    return value


def clean_string(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def parse_scalar(raw: str):
    value = raw.strip()
    if not value:
        return ""
    if value in {"true", "false"}:
        return value == "true"
    if value.startswith("[") and value.endswith("]"):
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return value
        return parsed if isinstance(parsed, list) else value
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def parse_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{path} missing frontmatter")

    data = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        data[key.strip()] = parse_scalar(value)
    return data


def post_url(relative_path: Path) -> str:
    parts = relative_path.parts
    if len(parts) < 4:
        return ""
    date_part = parts[-2]
    slug = relative_path.stem
    return f"https://feed.astralor.com/posts/{date_part}/{slug}/"


def valid_url(value) -> str:
    url = clean_string(value)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return url


def git_changed_posts(repo: Path, since: str) -> list[Path]:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "log",
            f"--since={since}",
            "--name-only",
            "--pretty=format:",
            "--",
            "src/data/blog/",
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    paths = []
    seen = set()
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or not line.endswith(".md"):
            continue
        if line in seen:
            continue
        seen.add(line)
        paths.append(Path(line))
    return sorted(paths)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("/data/code/github.com/astralor/feed"))
    parser.add_argument(
        "--state",
        type=Path,
        default=Path("/root/.openclaw/workspace/state/feed-broadcast.json"),
    )
    args = parser.parse_args()

    try:
        state = load_state(args.state)
        last_broadcast_at = clean_string(state.get("lastBroadcastAt")) or DEFAULT_STATE[
            "lastBroadcastAt"
        ]
        changed = git_changed_posts(args.repo, last_broadcast_at)
        posts = []
        for relative in changed:
            full_path = args.repo / relative
            if not full_path.exists():
                continue
            frontmatter = parse_frontmatter(full_path)
            posts.append(
                {
                    "path": str(relative),
                    "postUrl": post_url(relative),
                    "title": clean_string(frontmatter.get("title")),
                    "description": clean_string(frontmatter.get("description")),
                    "score": frontmatter.get("score"),
                    "featured": bool(frontmatter.get("featured")),
                    "category": clean_string(frontmatter.get("category")),
                    "tags": frontmatter.get("tags") if isinstance(frontmatter.get("tags"), list) else [],
                    "sourceUrl": valid_url(frontmatter.get("sourceUrl")),
                    "scoreReason": clean_string(frontmatter.get("scoreReason")),
                    "pubDatetime": clean_string(frontmatter.get("pubDatetime")),
                }
            )
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2

    print(
        json.dumps(
            {"ok": True, "lastBroadcastAt": last_broadcast_at, "posts": posts},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
