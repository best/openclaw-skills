#!/usr/bin/env python3
"""Discord Thread 智能归档 v1.1.0

AI-powered thread archiving. No config file — all settings via env vars.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

API_BASE = "https://discord.com/api/v10"
USER_AGENT = "DiscordBot (https://openclaw.ai, 1.0)"
DEFAULT_GUILD_ID = "1083322462244175902"
DEFAULT_AI_MODEL = "claude-sonnet-4-6"

# Tier thresholds (msg_count → hours)
TIERS = [(3, 8), (20, 24), (float("inf"), 48)]


# ── Config ──────────────────────────────────────────────────

def load_env():
    """Load config from env vars, falling back to OpenClaw config."""
    env = {
        "token": os.environ.get("DISCORD_BOT_TOKEN", ""),
        "guild_id": os.environ.get("ARCHIVER_GUILD_ID", DEFAULT_GUILD_ID),
        "ai_base_url": os.environ.get("ARCHIVER_AI_BASE_URL", ""),
        "ai_api_key": os.environ.get("ARCHIVER_AI_API_KEY", ""),
        "ai_model": os.environ.get("ARCHIVER_AI_MODEL", DEFAULT_AI_MODEL),
    }

    # Fall back to OpenClaw config for missing values
    oc = _load_openclaw_config()
    if oc:
        if not env["token"]:
            env["token"] = oc.get("channels", {}).get("discord", {}).get("token", "")
        if not env["ai_base_url"] or not env["ai_api_key"]:
            for prov in oc.get("models", {}).get("providers", {}).values():
                ids = [m.get("id", "") for m in prov.get("models", [])]
                if env["ai_model"] in ids:
                    env["ai_base_url"] = env["ai_base_url"] or prov.get("baseUrl", "")
                    env["ai_api_key"] = env["ai_api_key"] or prov.get("apiKey", "")
                    break
    return env


def _load_openclaw_config():
    p = Path("/root/.openclaw/openclaw.json")
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return None
    return None


# ── Discord API ─────────────────────────────────────────────

def discord_get(token, path):
    req = urllib.request.Request(f"{API_BASE}{path}")
    req.add_header("Authorization", f"Bot {token}")
    req.add_header("User-Agent", USER_AGENT)
    return json.loads(urllib.request.urlopen(req).read())


def discord_patch(token, path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{API_BASE}{path}", data=data, method="PATCH")
    req.add_header("Authorization", f"Bot {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", USER_AGENT)
    return json.loads(urllib.request.urlopen(req).read())


def discord_messages(token, channel_id, limit=8):
    try:
        return discord_get(token, f"/channels/{channel_id}/messages?limit={limit}")
    except urllib.error.HTTPError:
        return []


# ── AI Judge ────────────────────────────────────────────────

def ai_judge(env, thread_name, messages, verbose=False):
    """Ask LLM: is this conversation concluded? Returns concluded|ongoing|uncertain."""
    if not env["ai_base_url"] or not env["ai_api_key"]:
        if verbose:
            print("    AI: no API config, skip")
        return "uncertain"

    lines = []
    for msg in reversed(messages):
        author = msg.get("author", {}).get("username", "?")
        bot = " [bot]" if msg.get("author", {}).get("bot") else ""
        text = msg.get("content", "")[:200]
        if text:
            lines.append(f"{author}{bot}: {text}")
    if not lines:
        return "uncertain"

    prompt = (
        f"判断以下 Discord 对话是否已结束。\n\n"
        f"Thread: {thread_name}\n\n"
        + "\n".join(lines[-8:])
        + "\n\n只回答一个词: concluded / ongoing / uncertain"
    )

    try:
        body = json.dumps({
            "model": env["ai_model"],
            "max_tokens": 20,
            "messages": [{"role": "user", "content": prompt}],
        }).encode()
        req = urllib.request.Request(
            f"{env['ai_base_url']}/v1/messages", data=body, method="POST"
        )
        req.add_header("x-api-key", env["ai_api_key"])
        req.add_header("anthropic-version", "2023-06-01")
        req.add_header("Content-Type", "application/json")

        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())
        answer = ""
        for block in result.get("content", []):
            if block.get("type") == "text":
                answer = block["text"].strip().lower()
                break

        if verbose:
            print(f"    AI: {answer}")

        if "concluded" in answer:
            return "concluded"
        if "ongoing" in answer:
            return "ongoing"
        return "uncertain"
    except Exception as e:
        if verbose:
            print(f"    AI error: {e}")
        return "uncertain"


# ── Decision Engine ─────────────────────────────────────────

def tier_hours(msg_count):
    for max_msgs, hours in TIERS:
        if msg_count <= max_msgs:
            return hours
    return 48


def hours_inactive(iso_str):
    if not iso_str:
        return 0
    dt = datetime.fromisoformat(iso_str)
    return (datetime.now(timezone.utc) - dt).total_seconds() / 3600


def decide(env, thread, messages, verbose=False):
    """Return (should_archive, reason)."""
    meta = thread.get("thread_metadata", {})
    name = thread["name"]
    msgs = thread.get("message_count", 0)
    inactive = hours_inactive(meta.get("archive_timestamp", ""))

    # Hard rules
    if thread.get("last_pin_timestamp"):
        return False, "pinned"
    if inactive < 2:
        return False, f"recent ({inactive:.1f}h)"

    # Bot-only
    if messages:
        has_human = any(not m.get("author", {}).get("bot", False) for m in messages)
        if not has_human and inactive >= 4:
            return True, "bot-only, 4h+"

    # AI judgment (4h+ inactive)
    if inactive >= 4 and messages:
        verdict = ai_judge(env, name, messages, verbose)
        if verdict == "concluded":
            return True, f"AI: concluded ({inactive:.0f}h)"
        if verdict == "ongoing":
            limit = tier_hours(msgs) * 1.5
            if inactive >= limit:
                return True, f"AI: ongoing but {inactive:.0f}h > {limit:.0f}h"
            return False, f"AI: ongoing ({inactive:.0f}h < {limit:.0f}h)"

    # Time fallback
    limit = tier_hours(msgs)
    if inactive >= limit:
        return True, f"time: {inactive:.0f}h >= {limit:.0f}h"
    return False, f"active ({inactive:.0f}h < {limit:.0f}h)"


# ── Main ────────────────────────────────────────────────────

def main():
    dry_run = "--dry-run" in sys.argv
    verbose = "--verbose" in sys.argv
    env = load_env()

    if not env["token"]:
        print("ERROR: DISCORD_BOT_TOKEN not set"); sys.exit(1)

    print(f"=== Discord Thread 智能归档 v1.1.0 ===")
    print(f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"AI: {env['ai_model']}")
    print(f"模式: {'预览' if dry_run else '执行'}\n")

    data = discord_get(env["token"], f"/guilds/{env['guild_id']}/threads/active")
    threads = data.get("threads", [])

    archived, kept, failed, ai_calls = [], [], 0, 0

    for t in threads:
        if t.get("thread_metadata", {}).get("archived"):
            continue

        name, tid = t["name"], t["id"]
        if verbose:
            print(f"  评估: {name} ({t.get('message_count', 0)}条)")

        msgs = discord_messages(env["token"], tid)
        time.sleep(0.3)

        should, reason = decide(env, t, msgs, verbose)
        if "AI:" in reason:
            ai_calls += 1

        if should:
            if dry_run:
                print(f"  [预览] {name} — {reason}")
            else:
                try:
                    discord_patch(env["token"], f"/channels/{tid}", {"archived": True})
                    print(f"  ✓ {name} — {reason}")
                except urllib.error.HTTPError as e:
                    print(f"  ✗ {name}: HTTP {e.code}")
                    failed += 1
                    continue
                time.sleep(0.5)
            archived.append({"name": name, "reason": reason})
        else:
            if verbose:
                print(f"  [保留] {name} — {reason}")
            kept.append({"name": name, "reason": reason})

    print(f"\n结果: 归档 {len(archived)}, 保留 {len(kept)}, 失败 {failed}, AI {ai_calls}次")
    if archived:
        print("\n归档:")
        for a in archived:
            print(f"  - {a['name']} ({a['reason']})")

    report = {"archived": len(archived), "kept": len(kept), "failed": failed,
              "ai_calls": ai_calls, "details": archived}
    print(f"\n{json.dumps(report, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
