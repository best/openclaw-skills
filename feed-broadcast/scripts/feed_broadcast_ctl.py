#!/usr/bin/env python3
"""Controlled AI Feed broadcast runner."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DEFAULT_STATE = {"lastBroadcastAt": "1970-01-01T00:00:00Z"}


def now_cst() -> datetime:
    return datetime.now(timezone(timedelta(hours=8)))


def run(cmd: list[str], cwd: Path | None = None, check: bool = True, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text("utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", "utf-8")


def prepare(args: argparse.Namespace) -> dict[str, Any]:
    repo = args.repo.resolve()
    state = args.state.resolve()
    run(["git", "pull", "--quiet", "--rebase", "--autostash"], cwd=repo)
    script = Path(__file__).with_name("extract-new-posts.py")
    result = run([sys.executable, str(script), "--repo", str(repo), "--state", str(state)])
    extracted = json.loads(result.stdout)
    if not extracted.get("ok"):
        raise RuntimeError(extracted.get("error") or "extract-new-posts failed")
    posts = extracted.get("posts") or []
    task_path = args.task.resolve()
    write_json(
        task_path,
        {
            "ok": True,
            "lastBroadcastAt": extracted.get("lastBroadcastAt"),
            "posts": posts,
            "decisionPath": str(args.decision.resolve()),
            "statePath": str(state),
            "targetChannel": args.target,
            "logChannel": args.log_target,
            "instructions": {
                "publishThreshold": "featured=true or score>=8 must push; score 7.0-7.9 optional; below 7 default skip",
                "messageFormat": "Discord plain text only. Wrap links in <>. No tables, cards, components, or effects.",
                "decisionSchema": {
                    "status": "ok | no_content",
                    "selected": [{"path": "src/data/blog/YYYY-MM-DD/file.md", "reason": "why worth pushing"}],
                    "skipped": [{"path": "src/data/blog/YYYY-MM-DD/file.md", "reason": "why skipped"}],
                    "message": "broadcast body or empty when selected=[]",
                },
            },
        },
    )
    status = "no_content" if not posts else "needs_decision"
    return {"status": status, "posts": len(posts), "task": str(task_path), "decision": str(args.decision.resolve()), "message": "no new posts" if not posts else f"review {len(posts)} new posts"}


def validate_decision(decision: dict[str, Any], task: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    posts = task.get("posts") or []
    by_path = {post.get("path"): post for post in posts if isinstance(post, dict)}
    selected = decision.get("selected") or []
    skipped = decision.get("skipped") or []
    if not isinstance(selected, list) or not isinstance(skipped, list):
        raise RuntimeError("decision selected/skipped must be arrays")
    selected_paths = []
    for item in selected:
        path = item.get("path") if isinstance(item, dict) else None
        if path not in by_path:
            raise RuntimeError(f"selected unknown path: {path}")
        selected_paths.append(path)
    if len(selected_paths) != len(set(selected_paths)):
        raise RuntimeError("decision selected contains duplicate paths")
    missing_required = []
    for post in posts:
        try:
            score = float(post.get("score") or 0)
        except (TypeError, ValueError):
            score = 0
        if (post.get("featured") or score >= 8.0) and post.get("path") not in selected_paths:
            missing_required.append(post.get("path"))
    if missing_required:
        raise RuntimeError(f"featured/high-score posts must be selected: {missing_required}")
    message = decision.get("message") or ""
    if selected and not isinstance(message, str) or selected and not message.strip():
        raise RuntimeError("message is required when selected is non-empty")
    if not selected:
        message = ""
    return selected, skipped, message.strip()


def send_message(target: str, message: str, dry_run: bool, strict: bool = True) -> bool:
    if dry_run:
        return False
    result = run(["openclaw", "message", "send", "--channel", "discord", "--target", target, "--message", message], check=strict)
    return result.returncode == 0


def finalize(args: argparse.Namespace) -> dict[str, Any]:
    task = load_json(args.task.resolve())
    if not isinstance(task, dict):
        raise RuntimeError("task file missing or invalid")
    posts = task.get("posts") or []
    if not posts:
        return {"status": "no_content", "pushed": 0, "skipped": 0, "sent": False, "logSent": False, "message": "no new posts"}
    decision = load_json(args.decision.resolve())
    if not isinstance(decision, dict):
        raise RuntimeError("decision file missing or invalid")
    selected, skipped, message = validate_decision(decision, task)
    sent = False
    if selected:
        sent = send_message(args.target, message, args.dry_run, strict=True)
    log_sent = False
    if args.log_target and selected:
        log = f"📡 播报 {now_cst().strftime('%H:%M')} — 推送 {len(selected)} 条 / 跳过 {len(skipped)} 条"
        log_sent = send_message(args.log_target, log, args.dry_run, strict=False)
    stamp = now_cst().replace(microsecond=0).isoformat()
    if not args.dry_run:
        write_json(args.state.resolve(), {"lastBroadcastAt": stamp})
    return {"status": "ok", "dry_run": args.dry_run, "pushed": len(selected), "skipped": len(skipped), "sent": sent, "logSent": log_sent, "stateUpdated": not args.dry_run, "message": "broadcast finalized"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(os.environ["FEED_REPO"]) if os.environ.get("FEED_REPO") else None)
    parser.add_argument("--state", type=Path, default=Path(os.environ["FEED_BROADCAST_STATE"]) if os.environ.get("FEED_BROADCAST_STATE") else None)
    parser.add_argument("--task", type=Path, default=Path(os.environ.get("FEED_BROADCAST_TASK", "/tmp/feed-broadcast-task.json")))
    parser.add_argument("--decision", type=Path, default=Path(os.environ.get("FEED_BROADCAST_DECISION", "/tmp/feed-broadcast-decision.json")))
    parser.add_argument("--target", default=os.environ.get("FEED_BROADCAST_TARGET"))
    parser.add_argument("--log-target", default=os.environ.get("FEED_BROADCAST_LOG_TARGET", ""))
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prepare").set_defaults(func=prepare)
    final = sub.add_parser("finalize")
    final.add_argument("--dry-run", action="store_true")
    final.set_defaults(func=finalize)
    args = parser.parse_args()
    missing = []
    if not args.repo:
        missing.append("FEED_REPO or --repo")
    if not args.state:
        missing.append("FEED_BROADCAST_STATE or --state")
    if not args.target:
        missing.append("FEED_BROADCAST_TARGET or --target")
    if missing:
        print(json.dumps({"status": "failed", "message": "missing " + ", ".join(missing)}, ensure_ascii=False, indent=2))
        return 1
    try:
        print(json.dumps(args.func(args), ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "failed", "message": str(exc)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
