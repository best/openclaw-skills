#!/usr/bin/env python3
"""Deterministic AI Feed collection runner."""

from __future__ import annotations

import argparse
import base64
import html
import json
import os
import re
import subprocess
import sys
import tarfile
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

GENERATED_PATHS = [".astro", "dist", "node_modules/.astro", "public/pagefind"]
IGNORED_DIRTY_PATHS = ["data/scored-results.json", "src/data/blog"]
TRACKING_PARAMS = {"fbclid", "gclid", "mc_cid", "mc_eid"}
AI_KEYWORDS = re.compile(
    r"\b(ai|llm|agent|agents|model|models|openai|anthropic|claude|gemini|qwen|deepseek|rag|transformer|diffusion|inference|training|gpu|nvidia)\b",
    re.I,
)


def now_cst() -> datetime:
    return datetime.now(timezone(timedelta(hours=8)))


def collect_final(message: str, new_candidates: int, commit: str, pushed: bool) -> str:
    commit_label = commit or "none"
    return f"📡 采集完成 {now_cst().strftime('%H:%M')} — {message}; 新增 {new_candidates} 条; commit={commit_label}; pushed={str(pushed).lower()}"


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def http_json(url: str, headers: dict[str, str] | None = None, timeout: int = 45) -> Any:
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "feed-collect/2.2"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_text(url: str, headers: dict[str, str] | None = None, timeout: int = 45) -> str:
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "feed-collect/2.2"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def basic_auth_header(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {token}"


def load_miniflux_config() -> dict[str, str]:
    if os.environ.get("MINIFLUX_BASE_URL") and os.environ.get("MINIFLUX_USERNAME") and os.environ.get("MINIFLUX_PASSWORD"):
        return {
            "base_url": os.environ["MINIFLUX_BASE_URL"].rstrip("/"),
            "username": os.environ["MINIFLUX_USERNAME"],
            "password": os.environ["MINIFLUX_PASSWORD"],
        }

    config_path = os.environ.get("MINIFLUX_CONFIG")
    if not config_path:
        raise RuntimeError("MINIFLUX_CONFIG or MINIFLUX_BASE_URL/MINIFLUX_USERNAME/MINIFLUX_PASSWORD is required")
    path = Path(config_path)
    if not path.exists():
        raise RuntimeError("MINIFLUX_CONFIG does not exist")
    data = json.loads(path.read_text("utf-8"))
    for key in ["base_url", "username", "password"]:
        if not data.get(key):
            raise RuntimeError(f"miniflux config missing {key}")
    return {
        "base_url": str(data["base_url"]).rstrip("/"),
        "username": str(data["username"]),
        "password": str(data["password"]),
    }


def plain_text(value: str, limit: int = 600) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", value or "", flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def normalize_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url.strip())
    host = parsed.netloc.lower()
    path = parsed.path
    if host in {"arxiv.org", "www.arxiv.org", "export.arxiv.org"}:
        match = re.search(r"/(?:abs|pdf)/([^/?#]+)", path)
        if match:
            paper_id = re.sub(r"\.pdf$", "", match.group(1))
            paper_id = re.sub(r"v\d+$", "", paper_id)
            return f"https://arxiv.org/abs/{paper_id}"
    query = []
    for key, value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True):
        lower = key.lower()
        if lower.startswith("utm_") or lower in TRACKING_PARAMS:
            continue
        query.append((key, value))
    return urllib.parse.urlunparse(
        (
            parsed.scheme or "https",
            parsed.netloc,
            parsed.path.rstrip("/") or "/",
            "",
            urllib.parse.urlencode(query),
            "",
        )
    )


def source_type(name: str) -> str:
    normalized = name.lower()
    rules = [
        ("anthropic", "anthropic-blog"),
        ("openai", "openai-blog"),
        ("deepmind", "deepmind-blog"),
        ("meta ai", "meta-ai-blog"),
        ("google", "google-ai-blog"),
        ("microsoft", "microsoft-research"),
        ("techcrunch", "techcrunch"),
        ("verge", "the-verge"),
        ("wired", "wired"),
        ("ars technica", "ars-technica"),
        ("venturebeat", "venturebeat"),
        ("mit", "mit-tech-review"),
        ("arxiv", "arxiv"),
        ("36kr", "36kr"),
        ("36氪", "36kr"),
        ("aibase", "aibase"),
        ("ai日报", "aibase"),
        ("虎嗅", "huxiu"),
        ("少数派", "sspai"),
        ("hugging face", "huggingface-blog"),
        ("pytorch", "pytorch-blog"),
        ("github blog", "github-blog"),
        ("simon willison", "simon-willison"),
        ("lilian", "lilian-weng"),
        ("hacker news", "hacker-news"),
        ("github trending", "github-trending"),
    ]
    for needle, value in rules:
        if needle in normalized:
            return value
    return "other"


def load_candidates(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text("utf-8"))
    if not isinstance(data, list):
        raise RuntimeError("data/candidates.json must be a JSON array")
    return data


def load_seen(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "description": "URL/title dedup store for AI Feed collection. Schema: object with entries dict.",
            "entries": {},
        }
    data = json.loads(path.read_text("utf-8"))
    if isinstance(data, list):
        now_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        return {
            "description": "URL/title dedup store for AI Feed collection. Schema: object with entries dict.",
            "entries": {
                normalize_url(value): {"seen_at": now_utc, "date": now_utc[:10], "title": ""}
                for value in data
                if isinstance(value, str) and value.startswith("http")
            },
        }
    if not isinstance(data, dict) or not isinstance(data.get("entries"), dict):
        raise RuntimeError("data/seen.json must be an object with entries dict")
    return data


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", "utf-8")


def prepare_repo(repo: Path, allow_dirty_data: bool = False, dry_run: bool = False) -> None:
    generated_dirty = run(["git", "status", "--porcelain", "--", *GENERATED_PATHS], cwd=repo).stdout.strip()
    if generated_dirty and not dry_run:
        backup_dir = repo / ".git" / "feed-cron-backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"generated-artifacts-{now_cst().strftime('%Y%m%d-%H%M%S')}.tgz"
        with tarfile.open(backup_path, "w:gz") as tar:
            for rel in GENERATED_PATHS:
                path = repo / rel
                if path.exists():
                    tar.add(path, arcname=rel)
        run(["git", "restore", "--", *GENERATED_PATHS], cwd=repo, check=False)
        run(["git", "clean", "-fd", "--", *GENERATED_PATHS], cwd=repo, check=False)
        print(f"cleaned generated artifacts; backup={backup_path}", file=sys.stderr)

    excluded = [":!.astro", ":!dist", ":!node_modules/.astro", ":!public/pagefind"]
    excluded.extend(f":!{path}" for path in IGNORED_DIRTY_PATHS)
    if allow_dirty_data:
        excluded.extend([":!data/candidates.json", ":!data/seen.json"])
    status = run(["git", "status", "--porcelain", "--", ".", *excluded], cwd=repo).stdout.strip()
    if status:
        raise RuntimeError("non-generated dirty files remain:\n" + status)
    if not dry_run:
        run(["git", "pull", "--rebase", "--autostash"], cwd=repo)


def fetch_miniflux() -> tuple[list[dict[str, Any]], dict[str, str]]:
    config = load_miniflux_config()
    limit = int(os.environ.get("MINIFLUX_LIMIT", "200"))
    offset = 0
    entries: list[dict[str, Any]] = []
    headers = {
        "Authorization": basic_auth_header(config["username"], config["password"]),
        "User-Agent": "feed-collect/2.2",
    }
    while True:
        query = urllib.parse.urlencode(
            {"status": "unread", "order": "published_at", "direction": "desc", "limit": limit, "offset": offset}
        )
        data = http_json(f"{config['base_url']}/v1/entries?{query}", headers=headers)
        batch = data.get("entries") or []
        entries.extend(batch)
        total = int(data.get("total") or len(entries))
        if len(entries) >= total or not batch:
            break
        offset += limit
    return entries, config


def mark_miniflux_read(config: dict[str, str], ids: list[int], dry_run: bool) -> int:
    if not ids:
        return 0
    if dry_run:
        return 0
    payload = json.dumps({"entry_ids": ids, "status": "read"}).encode()
    headers = {
        "Authorization": basic_auth_header(config["username"], config["password"]),
        "Content-Type": "application/json",
        "User-Agent": "feed-collect/2.2",
    }
    req = urllib.request.Request(f"{config['base_url']}/v1/entries", data=payload, headers=headers, method="PUT")
    with urllib.request.urlopen(req, timeout=45):
        return len(ids)


def miniflux_candidates(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    collected_at = now_cst().replace(microsecond=0).isoformat()
    output = []
    for entry in entries:
        feed = entry.get("feed") or {}
        category = (feed.get("category") or {}).get("title") or "Other"
        source = feed.get("title") or "Miniflux"
        url = entry.get("url") or entry.get("external_url") or ""
        title = entry.get("title") or ""
        if not url or not title:
            continue
        output.append(
            {
                "title": title.strip(),
                "url": normalize_url(url),
                "source": source,
                "sourceType": source_type(source),
                "category": category,
                "pubDatetime": entry.get("published_at") or entry.get("created_at") or "",
                "snippet": plain_text(entry.get("content") or entry.get("summary") or title),
                "collectedAt": collected_at,
                "_miniflux_id": entry.get("id"),
            }
        )
    return output


def fetch_hn() -> list[dict[str, Any]]:
    limit = int(os.environ.get("HN_LIMIT", "20"))
    url = "https://hn.algolia.com/api/v1/search_by_date?" + urllib.parse.urlencode(
        {"query": "AI LLM agent model", "tags": "story", "numericFilters": "points>30", "hitsPerPage": limit}
    )
    data = http_json(url)
    collected_at = now_cst().replace(microsecond=0).isoformat()
    output = []
    for hit in data.get("hits", []):
        title = hit.get("title") or hit.get("story_title") or ""
        link = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        if not title or not link:
            continue
        output.append(
            {
                "title": title.strip(),
                "url": normalize_url(link),
                "source": "Hacker News",
                "sourceType": "hacker-news",
                "category": "Community",
                "pubDatetime": hit.get("created_at") or "",
                "snippet": f"HN points: {hit.get('points', 0)} · comments: {hit.get('num_comments', 0)}",
                "collectedAt": collected_at,
            }
        )
    return output


def fetch_github_trending() -> list[dict[str, Any]]:
    limit = int(os.environ.get("GITHUB_TRENDING_LIMIT", "20"))
    text = http_text("https://github.com/trending?since=daily", headers={"User-Agent": "Mozilla/5.0 feed-collect/2.2"})
    repos: list[str] = []
    for match in re.finditer(r'href="/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)"', text):
        repo = match.group(1)
        if repo not in repos:
            repos.append(repo)
    collected_at = now_cst().replace(microsecond=0).isoformat()
    output = []
    for repo in repos:
        if not AI_KEYWORDS.search(repo):
            continue
        output.append(
            {
                "title": repo,
                "url": normalize_url(f"https://github.com/{repo}"),
                "source": "GitHub Trending",
                "sourceType": "github-trending",
                "category": "Developer",
                "pubDatetime": "",
                "snippet": "Daily GitHub Trending repository matching AI keywords.",
                "collectedAt": collected_at,
            }
        )
        if len(output) >= limit:
            break
    return output


def prune_seen(seen: dict[str, Any]) -> None:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    entries = seen.setdefault("entries", {})
    seen["entries"] = {
        url: meta
        for url, meta in entries.items()
        if str(meta.get("date") or str(meta.get("seen_at", ""))[:10]) >= cutoff
    }


def commit_changes(repo: Path, do_push: bool, dry_run: bool) -> tuple[bool, str, bool]:
    if dry_run:
        return False, "", False
    run(["git", "add", "data/candidates.json", "data/seen.json"], cwd=repo)
    diff = run(["git", "diff", "--cached", "--quiet"], cwd=repo, check=False)
    if diff.returncode == 0:
        return False, "", False
    message = f"collect: {now_cst().strftime('%Y-%m-%d %H:%M')}"
    run(["git", "commit", "-m", message], cwd=repo)
    commit = run(["git", "rev-parse", "--short", "HEAD"], cwd=repo).stdout.strip()
    pushed = False
    if do_push:
        run(["git", "push"], cwd=repo)
        pushed = True
    return True, commit, pushed


def collect(args: argparse.Namespace) -> dict[str, Any]:
    repo = Path(os.environ.get("FEED_REPO", args.repo)).expanduser().resolve()
    prepare_repo(repo, allow_dirty_data=args.allow_dirty_data or args.dry_run, dry_run=args.dry_run)
    candidates_path = repo / "data" / "candidates.json"
    seen_path = repo / "data" / "seen.json"
    candidates = load_candidates(candidates_path)
    seen = load_seen(seen_path)
    existing_urls = {
        normalize_url(str(item.get("url", ""))) for item in candidates if isinstance(item, dict) and item.get("url")
    }
    seen_urls = set(seen.get("entries", {}).keys())

    warnings: list[str] = []
    miniflux_entries, config = fetch_miniflux()
    items = miniflux_candidates(miniflux_entries)
    try:
        hn_items = fetch_hn()
        items.extend(hn_items)
    except Exception as exc:
        warnings.append(f"HN skipped: {exc}")
        hn_items = []
    try:
        github_items = fetch_github_trending()
        items.extend(github_items)
    except Exception as exc:
        warnings.append(f"GitHub Trending skipped: {exc}")
        github_items = []

    new_items: list[dict[str, Any]] = []
    seen_this_run: set[str] = set()
    miniflux_ids: list[int] = []
    now_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    for item in items:
        url = normalize_url(str(item.get("url", "")))
        miniflux_id = item.get("_miniflux_id")
        if not url:
            continue
        if url in existing_urls or url in seen_urls or url in seen_this_run:
            if isinstance(miniflux_id, int):
                miniflux_ids.append(miniflux_id)
            continue
        public_item = {key: value for key, value in item.items() if not key.startswith("_")}
        public_item["url"] = url
        new_items.append(public_item)
        seen_this_run.add(url)
        if isinstance(miniflux_id, int):
            miniflux_ids.append(miniflux_id)
        seen.setdefault("entries", {})[url] = {
            "seen_at": now_utc,
            "date": now_utc[:10],
            "title": str(item.get("title", "")),
        }

    if new_items:
        candidates.extend(new_items)
        prune_seen(seen)
        if not args.dry_run:
            write_json(candidates_path, candidates)
            write_json(seen_path, seen)
        committed, commit, pushed = commit_changes(repo, args.push if args.commit else False, args.dry_run or not args.commit)
        marked = mark_miniflux_read(config, sorted(set(miniflux_ids)), args.dry_run)
        message = f"collected {len(new_items)} new candidates"
        return {
            "status": "ok",
            "dry_run": args.dry_run,
            "new_candidates": len(new_items),
            "miniflux_entries": len(miniflux_entries),
            "hn_items": len(hn_items),
            "github_items": len(github_items),
            "marked_read": marked,
            "committed": committed,
            "commit": commit,
            "pushed": pushed,
            "warnings": warnings,
            "message": message,
            "final": collect_final(message, len(new_items), commit, pushed),
        }

    marked = mark_miniflux_read(config, sorted(set(miniflux_ids)), args.dry_run)
    message = "no new candidates"
    return {
        "status": "no_content",
        "dry_run": args.dry_run,
        "new_candidates": 0,
        "miniflux_entries": len(miniflux_entries),
        "hn_items": len(hn_items),
        "github_items": len(github_items),
        "marked_read": marked,
        "committed": False,
        "commit": "",
        "pushed": False,
        "warnings": warnings,
        "message": message,
        "final": collect_final(message, 0, "", False),
    }


def verify(args: argparse.Namespace) -> dict[str, Any]:
    repo = Path(os.environ.get("FEED_REPO", args.repo)).expanduser().resolve()
    candidates = load_candidates(repo / "data" / "candidates.json")
    seen = load_seen(repo / "data" / "seen.json")
    bad_candidates = [
        index
        for index, item in enumerate(candidates)
        if not isinstance(item, dict) or not item.get("title") or not item.get("url")
    ]
    if bad_candidates:
        raise RuntimeError(f"invalid candidates at indexes {bad_candidates[:10]}")
    return {
        "status": "ok",
        "candidates": len(candidates),
        "seen_entries": len(seen.get("entries", {})),
        "message": "feed collect state is valid",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Feed deterministic collection runner")
    parser.add_argument("--repo", default=os.environ.get("FEED_REPO"))
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    collect_parser = subparsers.add_parser("collect")
    collect_parser.add_argument("--commit", action="store_true", default=False)
    collect_parser.add_argument("--push", action="store_true", default=False)
    collect_parser.add_argument("--dry-run", action="store_true", default=False)
    collect_parser.add_argument("--allow-dirty-data", action="store_true", default=False)
    collect_parser.set_defaults(func=collect)

    verify_parser = subparsers.add_parser("verify")
    verify_parser.set_defaults(func=verify)

    args = parser.parse_args()
    if not args.repo:
        print(json.dumps({"status": "failed", "message": "FEED_REPO or --repo is required"}, ensure_ascii=False, indent=2))
        return 1
    try:
        result = args.func(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "failed", "message": str(exc)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
