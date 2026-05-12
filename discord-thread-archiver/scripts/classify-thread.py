#!/usr/bin/env python3
"""Classify Discord threads for discord-thread-archiver.

Input JSON schema (stdin):
{
  "name": "thread title",
  "pinned": false,
  "lastMessageAgeMinutes": 123,
  "messages": [
    {"content": "...", "isBot": true},
    {"content": "...", "isBot": false}
  ],
  "operationalThreadPrefixes": ["🤖 "]
}

The agent is responsible for normalizing message-tool output into this small schema.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

ATTENTION = [
    "error", "failed", "blocked", "approval", "permission", "403",
    "异常", "失败", "阻塞", "等待确认", "需要用户", "需要人工", "权限不足",
]
RUNNING = [
    "running", "in progress", "started", "working",
    "执行中", "进行中", "等待结果", "还在跑",
]
DONE = [
    "finished", "completed", "done", " ok", "ok ", "summary",
    "任务完成", "已完成", "结果", "完成", "已发送", "已交付",
]
WAITING = [
    "wait for results", "waiting", "看看效果", "等结果", "触发一下", "待办", "需要你", "需要用户", "请确认",
]
CLOSURE = ["好了", "搞定", "done", "结束", "谢谢", "thanks", "确认", "没问题", "ok", "可以了"]
QUESTION_RE = re.compile(r"(？|\?|吗\s*$)")


def norm_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "bot"}
    return bool(value)


def msg_content(msg: dict[str, Any]) -> str:
    return str(msg.get("content") or msg.get("text") or msg.get("message") or "")


def msg_is_bot(msg: dict[str, Any]) -> bool:
    if "isBot" in msg:
        return norm_bool(msg["isBot"])
    if "bot" in msg:
        return norm_bool(msg["bot"])
    author = msg.get("author") or msg.get("sender") or {}
    if isinstance(author, dict):
        if "bot" in author:
            return norm_bool(author["bot"])
        if "isBot" in author:
            return norm_bool(author["isBot"])
    # Unknown author type is treated as human for safety.
    return False


def contains_any(text: str, needles: list[str]) -> bool:
    lower = text.lower()
    return any(n.lower() in lower for n in needles)


def verdict(verdict: str, reason_code: str, reason: str, thread_type: str) -> dict[str, Any]:
    return {
        "verdict": verdict,
        "reasonCode": reason_code,
        "reason": reason,
        "threadType": thread_type,
    }


def classify(data: dict[str, Any]) -> dict[str, Any]:
    name = str(data.get("name") or data.get("threadName") or "")
    prefixes = data.get("operationalThreadPrefixes") or ["🤖 "]
    if isinstance(prefixes, str):
        prefixes = [p for p in prefixes.split(",") if p]
    pinned = norm_bool(data.get("pinned") or data.get("last_pin_timestamp"))
    if pinned:
        return verdict("skip", "pinned", "pinned thread", "skip")

    try:
        age = float(data.get("lastMessageAgeMinutes"))
    except (TypeError, ValueError):
        age = None

    messages = data.get("messages") or []
    if not isinstance(messages, list):
        messages = []

    human_messages = [m for m in messages if isinstance(m, dict) and not msg_is_bot(m)]
    bot_messages = [m for m in messages if isinstance(m, dict) and msg_is_bot(m)]
    all_text = "\n".join(msg_content(m) for m in messages if isinstance(m, dict))
    last_msg = messages[-1] if messages and isinstance(messages[-1], dict) else {}
    last_text = msg_content(last_msg)
    last_from_bot = msg_is_bot(last_msg) if last_msg else False

    is_operational = any(name.startswith(str(prefix)) for prefix in prefixes) and not human_messages
    if is_operational:
        if contains_any(all_text, ATTENTION):
            return verdict("keep", "op_needs_attention", "bot-only operational thread needs attention", "operational")
        if contains_any(last_text or all_text, RUNNING):
            return verdict("keep", "op_running", "operational task still appears to be running", "operational")
        if contains_any(all_text, DONE):
            return verdict("archive", "op_done_no_human", "bot-only operational task completed", "operational")
        if age is not None and age >= 120:
            return verdict("archive", "op_stale_status_no_human", "old bot-only status thread with no attention signal", "operational")
        return verdict("keep", "op_recent_status", "recent bot-only status thread", "operational")

    # Normal conversation policy.
    human_text = "\n".join(msg_content(m) for m in human_messages)
    if human_text and contains_any(human_text, CLOSURE):
        return verdict("archive", "normal_closed", "human closure signal found", "normal")

    if last_from_bot and QUESTION_RE.search(last_text.strip()):
        return verdict("keep", "bot_question_unanswered", "last bot message is an unanswered question", "normal")

    if age is not None and age < 24 * 60:
        if human_messages:
            return verdict("keep", "collab_recent", "recent human-bot collaboration without closure", "normal")
        return verdict("keep", "recent_no_closure", "recent normal thread without closure", "normal")

    if not human_messages and bot_messages:
        return verdict("archive", "bot_only_old", "old bot-only thread", "normal")

    if contains_any(last_text or all_text, WAITING):
        return verdict("keep", "waiting_result", "thread implies pending result/action", "normal")

    if contains_any(all_text, ATTENTION):
        return verdict("keep", "waiting_answer", "thread contains blocker or manual action signal", "normal")

    if human_messages and contains_any(all_text, DONE):
        return verdict("archive", "collab_completed_old", "old collaboration appears completed", "normal")

    return verdict("keep", "uncertain", "cannot determine completion safely", "normal")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        data = json.load(sys.stdin)
        result = classify(data)
    except Exception as exc:  # noqa: BLE001 - CLI should return structured error
        result = {"verdict": "keep", "reasonCode": "classifier_error", "reason": str(exc), "threadType": "unknown"}
        print(json.dumps(result, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
