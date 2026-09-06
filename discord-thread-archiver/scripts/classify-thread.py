#!/usr/bin/env python3
"""Classify normalized Discord thread facts."""
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
    "wait for results", "waiting", "看看效果", "等结果", "触发一下", "待办",
    "需要你", "需要用户", "请确认",
]
CLOSURE = [
    "好了", "搞定", "done", "结束", "结束吧", "谢谢", "thanks", "确认", "没问题",
    "ok", "可以了", "完成", "完成了", "已完成", "完成吧", "收尾", "收工",
    "不再需要讨论", "不需要讨论了", "无需讨论", "不用讨论", "可以归档",
    "归档吧", "可以关闭", "关闭吧",
]
QUESTION_RE = re.compile(r"(？|\?|吗\s*$)")
FINAL_ANSWER_IDLE_MINUTES = 60
NEGATED_CLOSURE_RE = re.compile(
    r"(没|未|还没|尚未|无法|不能|没法|不).{0,6}(完成|结束|搞定|归档|关闭|收尾|收工)"
)
CLOSURE_QUESTION_RE = re.compile(
    r"(完成|结束|搞定|归档|关闭|收尾|收工).{0,4}(吗|么|\?|？)"
)


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
    return False


def msg_id(msg: dict[str, Any]) -> int | None:
    value = msg.get("messageId")
    if value is None:
        value = msg.get("id")
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def contains_any(text: str, needles: list[str]) -> bool:
    lower = text.lower()
    return any(needle.lower() in lower for needle in needles)


def has_closure_signal(text: str) -> bool:
    if not text:
        return False
    if NEGATED_CLOSURE_RE.search(text) or CLOSURE_QUESTION_RE.search(text):
        return False
    return contains_any(text, CLOSURE)


def verdict(name: str, reason_code: str, reason: str, thread_type: str) -> dict[str, Any]:
    return {
        "verdict": name,
        "reasonCode": reason_code,
        "reason": reason,
        "threadType": thread_type,
    }


def validate_messages(data: dict[str, Any], messages: list[Any]) -> dict[str, Any] | None:
    if not messages:
        return verdict("keep", "facts_invalid", "messages are required", "unknown")
    if data.get("messageOrder") != "oldest_to_newest":
        return verdict("keep", "facts_invalid", "messageOrder must be oldest_to_newest", "unknown")
    if not norm_bool(data.get("historyScanComplete")):
        return verdict("keep", "facts_incomplete", "historical participation scan is incomplete", "unknown")

    ids: list[int] = []
    for message in messages:
        if not isinstance(message, dict):
            return verdict("keep", "facts_invalid", "every message must be an object", "unknown")
        message_id = msg_id(message)
        if message_id is None:
            return verdict("keep", "facts_invalid", "every message needs a numeric messageId", "unknown")
        ids.append(message_id)

    if len(ids) != len(set(ids)):
        return verdict("keep", "facts_invalid", "duplicate message IDs", "unknown")
    if any(current >= following for current, following in zip(ids, ids[1:])):
        return verdict("keep", "facts_invalid", "message IDs must be strictly increasing", "unknown")
    return None


def classify(data: dict[str, Any]) -> dict[str, Any]:
    name = str(data.get("name") or data.get("threadName") or "")
    prefixes = data.get("operationalThreadPrefixes") or ["🤖 "]
    if isinstance(prefixes, str):
        prefixes = [prefix for prefix in prefixes.split(",") if prefix]

    pinned = norm_bool(data.get("pinned") or data.get("last_pin_timestamp"))
    if pinned:
        return verdict("skip", "pinned", "pinned thread", "skip")

    messages = data.get("messages") or []
    if not isinstance(messages, list):
        messages = []
    invalid = validate_messages(data, messages)
    if invalid is not None:
        return invalid

    try:
        age = float(data.get("lastMessageAgeMinutes"))
    except (TypeError, ValueError):
        age = None

    human_messages = [message for message in messages if not msg_is_bot(message)]
    bot_messages = [message for message in messages if msg_is_bot(message)]
    historical_human = (
        norm_bool(data.get("humanInitiated"))
        or norm_bool(data.get("hadHistoricalHumanParticipation"))
    )
    has_human = bool(human_messages) or historical_human

    all_text = "\n".join(msg_content(message) for message in messages)
    last_msg = messages[-1]
    last_text = msg_content(last_msg)
    last_from_bot = msg_is_bot(last_msg)

    if last_from_bot and QUESTION_RE.search(last_text.strip()):
        return verdict("keep", "bot_question_unanswered", "latest bot message is a question", "normal")
    if not last_from_bot and not has_closure_signal(last_text):
        return verdict("keep", "waiting_answer", "latest human message lacks a response", "normal")

    is_operational = (
        any(name.startswith(str(prefix)) for prefix in prefixes)
        and not has_human
    )
    if is_operational:
        if contains_any(all_text, ATTENTION):
            return verdict("keep", "op_needs_attention", "operational thread needs attention", "operational")
        if contains_any(last_text or all_text, RUNNING):
            return verdict("keep", "op_running", "operational task is running", "operational")
        if contains_any(all_text, DONE):
            return verdict("archive", "op_done_no_human", "operational task completed", "operational")
        if age is not None and age >= 120:
            return verdict("archive", "op_stale_status_no_human", "old status-only thread", "operational")
        return verdict("keep", "op_recent_status", "recent status-only thread", "operational")

    pending_indices: list[int] = []
    closure_indices: list[int] = []
    request_indices: list[int] = []
    for index, message in enumerate(messages):
        text = msg_content(message)
        human_closure = not msg_is_bot(message) and has_closure_signal(text)
        if human_closure:
            closure_indices.append(index)
        elif not msg_is_bot(message):
            request_indices.append(index)
        if not human_closure and (
            (msg_is_bot(message) and QUESTION_RE.search(text.strip()))
            or contains_any(text, WAITING)
            or contains_any(text, RUNNING)
            or contains_any(text, ATTENTION)
        ):
            pending_indices.append(index)

    if max(closure_indices, default=-1) > max(pending_indices + request_indices, default=-1):
        return verdict("archive", "normal_closed", "human closure follows pending signals", "normal")

    pending_signal = bool(pending_indices)
    if (
        last_from_bot
        and has_human
        and age is not None
        and FINAL_ANSWER_IDLE_MINUTES <= age < 24 * 60
        and not pending_signal
    ):
        return verdict(
            "archive", "collab_answered_idle",
            "final bot answer is idle without a pending signal", "normal",
        )

    if age is not None and age < 24 * 60:
        if has_human:
            return verdict("keep", "collab_recent", "recent collaboration lacks closure", "normal")
        return verdict("keep", "recent_no_closure", "recent normal thread lacks closure", "normal")

    if not has_human and bot_messages:
        return verdict("archive", "bot_only_old", "old bot-only thread", "normal")

    if contains_any(last_text or all_text, WAITING) or contains_any(last_text or all_text, RUNNING):
        return verdict("keep", "waiting_result", "result or action remains pending", "normal")
    if contains_any(all_text, ATTENTION):
        return verdict("keep", "waiting_answer", "blocker or manual action remains", "normal")
    if has_human and contains_any(all_text, DONE):
        return verdict("archive", "collab_completed_old", "old collaboration appears complete", "normal")

    return verdict("keep", "uncertain", "cannot determine completion safely", "normal")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        data = json.load(sys.stdin)
        result = classify(data)
    except Exception as exc:  # noqa: BLE001
        result = {
            "verdict": "keep",
            "reasonCode": "classifier_error",
            "reason": str(exc),
            "threadType": "unknown",
        }
        print(json.dumps(result, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
