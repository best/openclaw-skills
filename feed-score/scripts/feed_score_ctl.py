#!/usr/bin/env python3
"""Controlled AI Feed score/publish runner."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tarfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

GENERATED_PATHS = [".astro", "dist", "node_modules/.astro", "public/pagefind"]
ALLOWED_DIRTY_PATHS = ["data/candidates.json", "data/scored-results.json", "src/data/blog"]
DEFAULT_PUBLISH_THRESHOLD = 7.0


def now_cst() -> datetime:
    return datetime.now(timezone(timedelta(hours=8)))


def final_score_line(message: str, generated: int, cleanup_committed: bool, publish_pushed: bool, cleanup_pushed: bool) -> str:
    pushed = publish_pushed or cleanup_pushed
    return (
        f"📋 评分完成 {now_cst().strftime('%H:%M')} — {message}; "
        f"generated={generated}; cleanup={str(cleanup_committed).lower()}; pushed={str(pushed).lower()}"
    )


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check)


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text("utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", "utf-8")


def clean_generated(repo: Path, dry_run: bool = False) -> None:
    dirty = run(["git", "status", "--porcelain", "--", *GENERATED_PATHS], cwd=repo).stdout.strip()
    if not dirty or dry_run:
        return
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


def dangerous_dirty(repo: Path, allow_score_artifacts: bool) -> str:
    excluded = [":!.astro", ":!dist", ":!node_modules/.astro", ":!public/pagefind"]
    if allow_score_artifacts:
        excluded.extend(f":!{path}" for path in ALLOWED_DIRTY_PATHS)
    return run(["git", "status", "--porcelain", "--", ".", *excluded], cwd=repo).stdout.strip()


def prepare_repo(repo: Path, allow_score_artifacts: bool = False, dry_run: bool = False) -> None:
    clean_generated(repo, dry_run=dry_run)
    dirty = dangerous_dirty(repo, allow_score_artifacts=allow_score_artifacts)
    if dirty:
        raise RuntimeError("unexpected dirty files remain:\n" + dirty)
    if not dry_run:
        run(["git", "pull", "--rebase", "--autostash"], cwd=repo)


def normalize_url(value: str) -> str:
    value = value.strip() if isinstance(value, str) else ""
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return value.rstrip("/")


def load_candidates(repo: Path) -> list[dict[str, Any]]:
    data = load_json(repo / "data" / "candidates.json", [])
    if isinstance(data, dict):
        for key in ["candidates", "items", "entries"]:
            if isinstance(data.get(key), list):
                data = data[key]
                break
    if not isinstance(data, list):
        raise RuntimeError("data/candidates.json must be a list or object with list field")
    return data


def published_source_urls(repo: Path, days: int = 14) -> set[str]:
    urls: set[str] = set()
    blog = repo / "src" / "data" / "blog"
    if not blog.exists():
        return urls
    for offset in range(days):
        day = (now_cst() - timedelta(days=offset)).strftime("%Y-%m-%d")
        for path in (blog / day).glob("*.md"):
            for line in path.read_text("utf-8", errors="ignore").splitlines()[:40]:
                if line.startswith("sourceUrl:"):
                    url = line.split(":", 1)[1].strip().strip('"').strip("'")
                    normalized = normalize_url(url)
                    if normalized:
                        urls.add(normalized)
    return urls


def recent_titles(repo: Path, days: int = 7) -> list[str]:
    titles: list[str] = []
    blog = repo / "src" / "data" / "blog"
    if not blog.exists():
        return titles
    for offset in range(days):
        day = (now_cst() - timedelta(days=offset)).strftime("%Y-%m-%d")
        for path in sorted((blog / day).glob("*.md")):
            for line in path.read_text("utf-8", errors="ignore").splitlines()[:20]:
                if line.startswith("title:"):
                    titles.append(line.split(":", 1)[1].strip().strip('"'))
                    break
    return titles


def score_artifact_status(repo: Path) -> str:
    return run(["git", "status", "--porcelain", "--", "data/candidates.json", "data/scored-results.json", "src/data/blog"], cwd=repo).stdout.strip()


def make_task(args: argparse.Namespace) -> dict[str, Any]:
    repo = args.repo.resolve()
    prepare_repo(repo, allow_score_artifacts=True, dry_run=args.dry_run)
    candidates = load_candidates(repo)
    artifact_status = score_artifact_status(repo)
    scored_path = repo / "data" / "scored-results.json"
    if not candidates:
        if artifact_status:
            return {"status": "needs_cleanup", "candidates": 0, "dirty": artifact_status.splitlines(), "message": "score cleanup pending; run finalize"}
        message = "no candidates"
        return {"status": "no_content", "candidates": 0, "message": message, "final": final_score_line(message, 0, False, False, False)}
    if scored_path.exists() or any("src/data/blog/" in line for line in artifact_status.splitlines()):
        return {"status": "needs_finalize", "candidates": len(candidates), "dirty": artifact_status.splitlines(), "scoredResultsPath": str(scored_path.resolve()), "message": "score artifacts exist; run finalize"}
    batch = candidates[: args.limit]
    remaining = candidates[args.limit :]
    task = {
        "status": "needs_scoring",
        "repo": str(repo),
        "scoredResultsPath": str((repo / "data" / "scored-results.json").resolve()),
        "candidatesPath": str((repo / "data" / "candidates.json").resolve()),
        "scoringRulesPath": str((Path(__file__).resolve().parents[1] / "references" / "scoring-rules.md")),
        "batchSize": len(batch),
        "remainingCandidates": len(remaining),
        "publishedSourceUrls": sorted(published_source_urls(repo)),
        "recentTitles": recent_titles(repo),
        "candidates": batch,
        "instructions": {
            "write": "Write JSON object to scoredResultsPath. Do not modify repo files other than scored-results.json.",
            "schema": "Top-level object with evaluated, scoredAt, results[]. verdict is publish or skip.",
            "dedupe": "Do not compare current candidates against data/seen.json; compare only batch-internal URLs and publishedSourceUrls/recentTitles.",
            "threshold": f"score >= {args.publish_threshold:.1f} publish; lower scores must skip with reason low_score or duplicate.",
        },
    }
    write_json(args.task.resolve(), task)
    return {"status": "needs_scoring", "candidates": len(batch), "remainingCandidates": len(remaining), "task": str(args.task.resolve()), "scoredResultsPath": task["scoredResultsPath"], "message": f"score {len(batch)} candidates"}


def stage_paths(repo: Path, paths: list[str]) -> None:
    for rel in paths:
        path = repo / rel
        if path.exists():
            run(["git", "add", rel], cwd=repo)
        else:
            run(["git", "add", "-u", rel], cwd=repo, check=False)


def commit_if_needed(repo: Path, paths: list[str], message: str, push: bool, dry_run: bool) -> tuple[bool, str, bool]:
    if dry_run:
        return False, "", False
    stage_paths(repo, paths)
    diff = run(["git", "diff", "--cached", "--quiet"], cwd=repo, check=False)
    if diff.returncode == 0:
        return False, "", False
    run(["git", "commit", "-m", message], cwd=repo)
    commit = run(["git", "rev-parse", "--short", "HEAD"], cwd=repo).stdout.strip()
    pushed = False
    if push:
        run(["git", "push"], cwd=repo)
        pushed = True
    return True, commit, pushed


def build_repo(repo: Path, dry_run: bool) -> None:
    if dry_run:
        return
    run(["npm", "run", "build"], cwd=repo)


def finalize(args: argparse.Namespace) -> dict[str, Any]:
    repo = args.repo.resolve()
    prepare_repo(repo, allow_score_artifacts=True, dry_run=args.dry_run)
    candidates = load_candidates(repo)
    if not candidates:
        # Clean leftover scored-results deletion if present.
        if (repo / "data" / "scored-results.json").exists():
            if not args.dry_run:
                (repo / "data" / "scored-results.json").unlink()
        committed, commit, pushed = commit_if_needed(repo, ["data/candidates.json", "data/scored-results.json"], "score: clear processed candidates", args.push, args.dry_run)
        message = "no candidates; cleaned score artifacts"
        return {
            "status": "no_content",
            "generated": 0,
            "committed": committed,
            "commit": commit,
            "pushed": pushed,
            "message": message,
            "final": final_score_line(message, 0, committed, False, pushed),
        }

    scored = args.scored.resolve()
    if not scored.exists():
        raise RuntimeError(f"missing scored results: {scored}")
    validate = Path(__file__).with_name("validate-score-results.py")
    validate_cmd = [
        sys.executable,
        str(validate),
        str(scored),
        "--candidates",
        str(repo / "data" / "candidates.json"),
        "--publish-threshold",
        f"{args.publish_threshold:.1f}",
    ]
    task = load_json(args.task.resolve(), {}) if args.task.exists() else {}
    if isinstance(task, dict) and int(task.get("remainingCandidates") or 0) > 0:
        validate_cmd.append("--allow-partial")
    validation = run(validate_cmd)
    if args.dry_run:
        scored_data = load_json(scored, {})
        results = scored_data.get("results", []) if isinstance(scored_data, dict) else []
        publish_count = len([item for item in results if isinstance(item, dict) and item.get("verdict") == "publish"])
        skip_count = len([item for item in results if isinstance(item, dict) and item.get("verdict") == "skip"])
        message = f"validated {len(results)} scored results"
        return {"status": "ok", "dry_run": True, "validation": json.loads(validation.stdout), "generated": publish_count, "skipped": skip_count, "message": message, "final": final_score_line(message, publish_count, False, False, False)}
    generator = Path(__file__).with_name("generate-posts.py")
    generated = run([sys.executable, str(generator), str(scored), "--repo-dir", str(repo)])
    generated_summary = json.loads(generated.stdout)
    generated_count = int(generated_summary.get("generated") or 0)
    skipped_count = int(generated_summary.get("skipped") or 0)

    if generated_count > 0:
        build_repo(repo, args.dry_run)
        today = now_cst().strftime("%Y-%m-%d")
        yesterday = (now_cst() - timedelta(days=1)).strftime("%Y-%m-%d")
        paths = [f"src/data/blog/{today}", f"src/data/blog/{yesterday}"]
        committed, commit, pushed = commit_if_needed(repo, paths, f"feed: {today} - {generated_count} items", args.push, args.dry_run)
    else:
        committed, commit, pushed = False, "", False

    remaining: list[dict[str, Any]] = []
    if isinstance(task, dict) and isinstance(task.get("remainingCandidates"), int) and task.get("remainingCandidates"):
        remaining = candidates[int(task.get("batchSize", len(candidates))) :]
    if not args.dry_run:
        write_json(repo / "data" / "candidates.json", remaining)
        if (repo / "data" / "scored-results.json").exists():
            (repo / "data" / "scored-results.json").unlink()
    cleanup_committed, cleanup_commit, cleanup_pushed = commit_if_needed(repo, ["data/candidates.json", "data/scored-results.json"], "score: clear processed candidates", args.push, args.dry_run)
    message = f"generated {generated_count} posts; skipped {skipped_count}"
    return {
        "status": "ok",
        "dry_run": args.dry_run,
        "validation": json.loads(validation.stdout),
        "generated": generated_count,
        "skipped": skipped_count,
        "publishCommitted": committed,
        "publishCommit": commit,
        "publishPushed": pushed,
        "cleanupCommitted": cleanup_committed,
        "cleanupCommit": cleanup_commit,
        "cleanupPushed": cleanup_pushed,
        "remainingCandidates": len(remaining),
        "message": message,
        "final": final_score_line(message, generated_count, cleanup_committed, pushed, cleanup_pushed),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(os.environ["FEED_REPO"]) if os.environ.get("FEED_REPO") else None)
    parser.add_argument("--task", type=Path, default=Path(os.environ.get("FEED_SCORE_TASK", "/tmp/feed-score-task.json")))
    parser.add_argument("--scored", type=Path, default=Path(os.environ["FEED_SCORE_RESULTS"]) if os.environ.get("FEED_SCORE_RESULTS") else None)
    sub = parser.add_subparsers(dest="cmd", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--limit", type=int, default=int(os.environ.get("FEED_SCORE_LIMIT", "200")))
    prep.add_argument("--publish-threshold", type=float, default=float(os.environ.get("FEED_SCORE_PUBLISH_THRESHOLD", str(DEFAULT_PUBLISH_THRESHOLD))))
    prep.add_argument("--dry-run", action="store_true")
    prep.set_defaults(func=make_task)
    final = sub.add_parser("finalize")
    final.add_argument("--push", action="store_true")
    final.add_argument("--publish-threshold", type=float, default=float(os.environ.get("FEED_SCORE_PUBLISH_THRESHOLD", str(DEFAULT_PUBLISH_THRESHOLD))))
    final.add_argument("--dry-run", action="store_true")
    final.set_defaults(func=finalize)
    args = parser.parse_args()
    if not args.repo:
        print(json.dumps({"status": "failed", "message": "FEED_REPO or --repo is required"}, ensure_ascii=False, indent=2))
        return 1
    if args.cmd == "finalize" and not args.scored:
        args.scored = args.repo / "data" / "scored-results.json"
    try:
        print(json.dumps(args.func(args), ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "failed", "message": str(exc)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
