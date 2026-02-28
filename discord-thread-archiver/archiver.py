#!/usr/bin/env python3
"""Discord Thread 智能归档工具 v1.0.0

根据对话内容、消息量、频道类型和 AI 判断自动归档不活跃的 Thread。
配置化设计，所有参数可通过 config.json 调整。

用法:
    python3 archiver.py [--dry-run] [--verbose] [--config path/to/config.json]
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ============================================================
# 常量
# ============================================================
SCRIPT_DIR = Path(__file__).parent
DEFAULT_CONFIG = SCRIPT_DIR / "config.json"
API_BASE = "https://discord.com/api/v10"
USER_AGENT = "DiscordBot (https://openclaw.ai, 1.0)"

DEFAULT_CLOSING_PATTERNS = [
    r"谢谢", r"感谢", r"搞定", r"解决了", r"好的[，。！]?\s*$",
    r"OK[，。！]?\s*$", r"ok[，。！]?\s*$", r"收到", r"明白了",
    r"没问题", r"就这样", r"先这样", r"可以了", r"完美",
]


# ============================================================
# 配置加载
# ============================================================

def load_config(config_path=None):
    """加载配置文件，合并环境变量覆盖"""
    path = Path(config_path) if config_path else DEFAULT_CONFIG
    if path.exists():
        cfg = json.loads(path.read_text())
    else:
        cfg = {}

    # 环境变量覆盖
    if os.environ.get("ARCHIVER_AI_BASE_URL"):
        cfg.setdefault("ai", {})["base_url"] = os.environ["ARCHIVER_AI_BASE_URL"]
    if os.environ.get("ARCHIVER_AI_API_KEY"):
        cfg.setdefault("ai", {})["api_key"] = os.environ["ARCHIVER_AI_API_KEY"]

    # 从 OpenClaw 配置补全缺失的 token 和 AI 配置
    openclaw_config = _load_openclaw_config()
    if openclaw_config:
        if not cfg.get("_discord_token"):
            cfg["_discord_token"] = openclaw_config.get("channels", {}).get("discord", {}).get("token", "")

        ai = cfg.setdefault("ai", {})
        if not ai.get("base_url") or not ai.get("api_key"):
            # 从 providers 中找匹配的
            providers = openclaw_config.get("models", {}).get("providers", {})
            for name, prov in providers.items():
                models = prov.get("models", [])
                model_ids = [m.get("id", "") for m in models]
                if ai.get("model", "claude-sonnet-4-6") in model_ids:
                    if not ai.get("base_url"):
                        ai["base_url"] = prov.get("baseUrl", "")
                    if not ai.get("api_key"):
                        ai["api_key"] = prov.get("apiKey", "")
                    break

    # Discord token 也可以从环境变量来
    if os.environ.get("DISCORD_BOT_TOKEN"):
        cfg["_discord_token"] = os.environ["DISCORD_BOT_TOKEN"]

    return cfg


def _load_openclaw_config():
    """尝试加载 OpenClaw 配置（用于补全 token 和 API 配置）"""
    config_path = Path("/root/.openclaw/openclaw.json")
    if config_path.exists():
        try:
            return json.loads(config_path.read_text())
        except Exception:
            pass
    return None


# ============================================================
# Discord API
# ============================================================

def discord_get(token, path):
    req = urllib.request.Request(f"{API_BASE}{path}")
    req.add_header("Authorization", f"Bot {token}")
    req.add_header("User-Agent", USER_AGENT)
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def discord_patch(token, path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{API_BASE}{path}", data=data, method="PATCH")
    req.add_header("Authorization", f"Bot {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", USER_AGENT)
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def discord_get_messages(token, channel_id, limit=8):
    try:
        return discord_get(token, f"/channels/{channel_id}/messages?limit={limit}")
    except urllib.error.HTTPError:
        return []


# ============================================================
# AI 对话判断
# ============================================================

def ai_judge_concluded(cfg, thread_name, messages, verbose=False):
    """用 LLM 判断对话是否结束"""
    ai_cfg = cfg.get("ai", {})
    if not ai_cfg.get("enabled", True):
        return "uncertain"

    base_url = ai_cfg.get("base_url", "")
    api_key = ai_cfg.get("api_key", "")
    model = ai_cfg.get("model", "claude-sonnet-4-6")

    if not base_url or not api_key:
        if verbose:
            print("    AI: 缺少 API 配置，跳过")
        return "uncertain"

    # 构造对话摘要
    conversation = []
    for msg in reversed(messages):
        author = msg.get("author", {}).get("username", "unknown")
        is_bot = msg.get("author", {}).get("bot", False)
        role_tag = " [bot]" if is_bot else ""
        content = msg.get("content", "")[:200]
        if content:
            conversation.append(f"{author}{role_tag}: {content}")

    if not conversation:
        return "uncertain"

    conv_text = "\n".join(conversation[-8:])

    prompt = f"""判断以下 Discord 对话是否已经结束。

Thread 标题: {thread_name}

最近对话:
{conv_text}

请只回答一个词:
- concluded（对话已结束，问题已解决或讨论已收尾）
- ongoing（对话还在进行中，有未解决的问题或等待回复）
- uncertain（无法确定）"""

    try:
        url = f"{base_url}/v1/messages"
        body = {
            "model": model,
            "max_tokens": 20,
            "messages": [{"role": "user", "content": prompt}],
        }
        data = json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("x-api-key", api_key)
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
            print(f"    AI 判断: {answer}")

        if "concluded" in answer:
            return "concluded"
        elif "ongoing" in answer:
            return "ongoing"
        return "uncertain"

    except Exception as e:
        if verbose:
            print(f"    AI 调用失败: {e}")
        return "uncertain"


# ============================================================
# 归档决策引擎
# ============================================================

def get_tier_hours(cfg, msg_count, parent_id):
    """根据消息量和频道计算归档阈值（小时）"""
    tiers = cfg.get("tiers", {})
    quick = tiers.get("quick", {"max_msgs": 3, "hours": 8})
    normal = tiers.get("normal", {"max_msgs": 20, "hours": 24})
    deep = tiers.get("deep", {"max_msgs": 99999, "hours": 48})

    if msg_count <= quick["max_msgs"]:
        hours = quick["hours"]
    elif msg_count <= normal["max_msgs"]:
        hours = normal["hours"]
    else:
        hours = deep["hours"]

    multiplier = cfg.get("channel_multipliers", {}).get(parent_id, 1.0)
    return hours * multiplier


def hours_since(iso_str):
    if not iso_str:
        return 0
    dt = datetime.fromisoformat(iso_str)
    delta = datetime.now(timezone.utc) - dt
    return delta.total_seconds() / 3600


def decide_archive(cfg, thread, messages, verbose=False):
    """决定是否归档。返回 (should_archive, reason)"""
    meta = thread.get("thread_metadata", {})
    name = thread["name"]
    msg_count = thread.get("message_count", 0)
    parent_id = thread.get("parent_id", "")
    has_pins = bool(thread.get("last_pin_timestamp"))

    archive_ts = meta.get("archive_timestamp", "")
    inactive_hours = hours_since(archive_ts)

    # --- 硬规则 ---
    if has_pins:
        return False, "has pins (protected)"

    if inactive_hours < 2:
        return False, f"too recent ({inactive_hours:.1f}h)"

    # --- Bot-only ---
    if messages:
        human_msgs = [m for m in messages if not m.get("author", {}).get("bot", False)]
        if not human_msgs and inactive_hours >= 4:
            return True, "bot-only thread, 4h+ inactive"

    # --- 结束语 ---
    patterns = cfg.get("closing_patterns", DEFAULT_CLOSING_PATTERNS)
    if messages:
        last_content = messages[0].get("content", "")
        for pattern in patterns:
            if re.search(pattern, last_content):
                tier_hours = get_tier_hours(cfg, msg_count, parent_id) / 2
                if inactive_hours >= tier_hours:
                    return True, f"closing signal + {inactive_hours:.0f}h inactive"
                break

    # --- AI 判断 ---
    ai_cfg = cfg.get("ai", {})
    min_ai_hours = ai_cfg.get("min_inactive_hours", 4)
    if inactive_hours >= min_ai_hours and messages and ai_cfg.get("enabled", True):
        verdict = ai_judge_concluded(cfg, name, messages, verbose)
        if verdict == "concluded":
            return True, f"AI: concluded ({inactive_hours:.0f}h inactive)"
        elif verdict == "ongoing":
            tier_hours = get_tier_hours(cfg, msg_count, parent_id) * 1.5
            if inactive_hours >= tier_hours:
                return True, f"AI: ongoing but {inactive_hours:.0f}h > {tier_hours:.0f}h limit"
            return False, f"AI: ongoing ({inactive_hours:.0f}h < {tier_hours:.0f}h)"

    # --- 兜底时间规则 ---
    tier_hours = get_tier_hours(cfg, msg_count, parent_id)
    if inactive_hours >= tier_hours:
        return True, f"time rule: {inactive_hours:.0f}h >= {tier_hours:.0f}h"

    return False, f"active ({inactive_hours:.0f}h < {tier_hours:.0f}h)"


# ============================================================
# 主流程
# ============================================================

def main():
    dry_run = "--dry-run" in sys.argv
    verbose = "--verbose" in sys.argv
    config_path = None

    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--config" and i + 1 < len(args):
            config_path = args[i + 1]

    cfg = load_config(config_path)
    token = cfg.get("_discord_token", "")
    guild_id = cfg.get("guild_id", "")

    if not token:
        print("ERROR: Discord token not found")
        sys.exit(1)
    if not guild_id:
        print("ERROR: guild_id not configured")
        sys.exit(1)

    print("=== Discord Thread 智能归档 v1.0.0 ===")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Guild: {guild_id}")
    print(f"AI: {'启用' if cfg.get('ai', {}).get('enabled', True) else '禁用'} ({cfg.get('ai', {}).get('model', 'N/A')})")
    print(f"模式: {'预览' if dry_run else '执行'}")
    print()

    # 获取活跃 Thread
    data = discord_get(token, f"/guilds/{guild_id}/threads/active")
    threads = data.get("threads", [])

    archived_list = []
    kept_list = []
    failed = 0
    ai_calls = 0

    for t in threads:
        meta = t.get("thread_metadata", {})
        if meta.get("archived", False):
            continue

        name = t["name"]
        tid = t["id"]
        msg_count = t.get("message_count", 0)

        if verbose:
            print(f"  评估: {name} ({msg_count}条)")

        messages = discord_get_messages(token, tid, limit=8)
        time.sleep(0.3)

        should_archive, reason = decide_archive(cfg, t, messages, verbose)

        if "AI:" in reason:
            ai_calls += 1

        if should_archive:
            if dry_run:
                print(f"  [预览归档] {name} — {reason}")
                archived_list.append({"name": name, "reason": reason})
            else:
                try:
                    discord_patch(token, f"/channels/{tid}", {"archived": True})
                    print(f"  ✓ {name} — {reason}")
                    archived_list.append({"name": name, "reason": reason})
                    time.sleep(0.5)
                except urllib.error.HTTPError as e:
                    print(f"  ✗ {name}: HTTP {e.code}")
                    failed += 1
        else:
            if verbose:
                print(f"  [保留] {name} — {reason}")
            kept_list.append({"name": name, "reason": reason})

    print()
    print(f"结果: 归档 {len(archived_list)}, 保留 {len(kept_list)}, 失败 {failed}, AI调用 {ai_calls}")

    if archived_list:
        print("\n归档列表:")
        for item in archived_list:
            print(f"  - {item['name']} ({item['reason']})")

    if verbose and kept_list:
        print("\n保留列表:")
        for item in kept_list:
            print(f"  - {item['name']} ({item['reason']})")

    report = {
        "archived": len(archived_list),
        "kept": len(kept_list),
        "failed": failed,
        "ai_calls": ai_calls,
        "details": archived_list,
    }
    print(f"\n{json.dumps(report, ensure_ascii=False)}")
    return report


if __name__ == "__main__":
    main()
