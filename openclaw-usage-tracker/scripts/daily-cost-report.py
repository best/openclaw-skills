#!/usr/bin/env python3
"""OpenClaw Usage Tracker — model usage + token/cost accounting

This script scans OpenClaw session transcripts (*.jsonl) across all agents and
aggregates token usage + cost by date, category (interactive/cron/heartbeat),
provider, and model.

Usage:
  python3 daily-cost-report.py                          # yesterday
  python3 daily-cost-report.py 2026-03-14               # single day
  python3 daily-cost-report.py 2026-03-10 2026-03-15    # date range (inclusive)
  python3 daily-cost-report.py --all                    # full history
  python3 daily-cost-report.py 2026-03-14 --top-sessions 10
  python3 daily-cost-report.py --all --top-sessions 5

Output:
  JSON, schema described in SKILL.md.
"""

import argparse
import datetime
import json
import os
from collections import defaultdict


def parse_args():
    p = argparse.ArgumentParser(description="OpenClaw usage & cost report")
    p.add_argument(
        "dates",
        nargs="*",
        help="Single date (YYYY-MM-DD) or range (FROM TO)",
    )
    p.add_argument("--all", action="store_true", help="Scan all history")
    p.add_argument(
        "--top-sessions",
        type=int,
        default=0,
        metavar="N",
        help="Include top N most expensive sessions",
    )
    p.add_argument(
        "--format",
        choices=["json", "discord"],
        default="json",
        help="Output format: json (default) or discord (pre-formatted text)",
    )
    p.add_argument(
        "--trend-days",
        type=int,
        default=0,
        metavar="N",
        help="Append N-day trend summary (discord format only, runs extra scan)",
    )
    return p.parse_args()


def load_cost_map():
    config_path = os.path.expanduser("~/.openclaw/openclaw.json")
    with open(config_path) as f:
        cfg = json.load(f)

    cost_map = {}
    for pname, pdata in cfg.get("models", {}).get("providers", {}).items():
        for m in pdata.get("models", []):
            key = f"{pname}/{m['id']}"
            cost = m.get("cost")
            if cost:
                cost_map[key] = cost

    return cost_map


def _extract_text(msg):
    content = msg.get("content", "")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                return block.get("text", "")
        return ""
    return content if isinstance(content, str) else ""


def build_session_classification():
    """Build category map + optional session metadata for top-sessions."""

    agents_dir = os.path.expanduser("~/.openclaw/agents")
    file_category = {}  # basename -> category
    session_meta = {}  # basename -> {key, agent}

    for agent in os.listdir(agents_dir):
        sfile = os.path.join(agents_dir, agent, "sessions", "sessions.json")
        if os.path.isfile(sfile):
            try:
                with open(sfile) as f:
                    store = json.load(f)
                for key, entry in store.items():
                    cat = (
                        "cron"
                        if "cron:" in key
                        else "heartbeat"
                        if "heartbeat" in key
                        else "interactive"
                    )
                    sf = entry.get("sessionFile", "")
                    if sf:
                        bn = os.path.basename(sf).replace(".jsonl", "")
                        file_category[bn] = cat
                        session_meta[bn] = {"key": key, "agent": agent}
                    sid = entry.get("sessionId", "")
                    if sid:
                        file_category[sid] = cat
                        session_meta[sid] = {"key": key, "agent": agent}
            except Exception:
                pass

        # Content-based fallback for orphaned sessions: detect leading [cron:...]
        sessions_dir = os.path.join(agents_dir, agent, "sessions")
        if not os.path.isdir(sessions_dir):
            continue
        for fname in os.listdir(sessions_dir):
            if not fname.endswith(".jsonl"):
                continue
            basename = fname.replace(".jsonl", "")
            if basename in file_category:
                continue
            if "_" in basename:
                uuid_part = basename.split("_", 1)[1]
                if uuid_part in file_category:
                    continue

            fpath = os.path.join(sessions_dir, fname)
            try:
                with open(fpath) as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            msg = entry.get("message", {})
                            if isinstance(msg, dict) and msg.get("role") == "user":
                                content = _extract_text(msg)
                                if content.startswith("[cron:"):
                                    file_category[basename] = "cron"
                                break
                        except Exception:
                            continue
            except Exception:
                pass

    return file_category, session_meta


def classify(fname, file_category):
    basename = fname.replace(".jsonl", "")
    if basename in file_category:
        return file_category[basename]
    if "_" in basename:
        uuid_part = basename.split("_", 1)[1]
        if uuid_part in file_category:
            return file_category[uuid_part]
    return "interactive"


def fmt_tokens(n):
    if n >= 1_000_000_000:
        return f"{n/1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def short_provider(provider):
    return {
        "astralor": "astralor",
        "gptclub-openai": "gptclub",
        "gptclub-claude": "gptclub",
        "gptclub-google": "gptclub",
        "deeprouter": "deeprouter",
        "minimax": "minimax",
        "kimi-coding": "kimi",
    }.get(provider, provider or "unknown")


def short_model_name(model_id):
    # Anthropic models (common in this setup)
    # claude-opus-4-6 -> Opus-4.6
    if model_id.startswith("claude-"):
        parts = model_id.split("-")
        # claude, <tier>, <major>, <minor>
        if len(parts) >= 4:
            tier = parts[1].capitalize()
            major = parts[2]
            minor = parts[3]
            if major.isdigit() and minor.isdigit():
                return f"{tier}-{major}.{minor}"
    # OpenAI-ish models
    if model_id.startswith("gpt-"):
        return model_id.upper()
    # MiniMax models
    if model_id.startswith("MiniMax-"):
        return model_id.replace("MiniMax-", "")
    return model_id


def split_model_key(mk):
    if "/" in mk:
        provider, model_id = mk.split("/", 1)
        return provider, model_id
    return "unknown", mk


def display_model_key(mk):
    provider, model_id = split_model_key(mk)
    return f"{short_provider(provider)}/{short_model_name(model_id)}"


def extract_usage(usage):
    """Extract token counts from various usage field formats."""

    inp = usage.get(
        "input",
        usage.get(
            "inputTokens",
            usage.get("input_tokens", usage.get("promptTokens", 0)),
        ),
    ) or 0
    out = usage.get(
        "output",
        usage.get(
            "outputTokens",
            usage.get("output_tokens", usage.get("completionTokens", 0)),
        ),
    ) or 0
    cr = usage.get(
        "cacheRead",
        usage.get(
            "cache_read",
            usage.get(
                "cache_read_input_tokens",
                usage.get("cached_tokens", 0),
            ),
        ),
    ) or 0
    if cr == 0:
        ptd = usage.get("prompt_tokens_details", {})
        if isinstance(ptd, dict):
            cr = ptd.get("cached_tokens", 0) or 0
    cw = usage.get(
        "cacheWrite",
        usage.get("cache_write", usage.get("cache_creation_input_tokens", 0)),
    ) or 0
    return inp, out, cr, cw


def calc_cost(usage, mk, cost_map):
    """Calculate cost: prefer provider-returned, fallback to config estimate."""

    usage_cost = usage.get("cost")
    if isinstance(usage_cost, dict) and usage_cost.get("total") is not None:
        return usage_cost["total"]

    inp, out, cr, cw = extract_usage(usage)
    if mk in cost_map:
        c = cost_map[mk]
        return (
            inp * c.get("input", 0)
            + out * c.get("output", 0)
            + cr * c.get("cacheRead", 0)
            + cw * c.get("cacheWrite", 0)
        ) / 1_000_000

    return 0.0


def date_matches(ts, date_from, date_to):
    """Check if timestamp string falls within date range (inclusive)."""

    if not isinstance(ts, str) or len(ts) < 10:
        return False
    day = ts[:10]
    return date_from <= day <= date_to


def get_first_user_message(fpath):
    """Read first user message from a .jsonl file for session preview."""

    try:
        with open(fpath) as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    msg = entry.get("message", {})
                    if isinstance(msg, dict) and msg.get("role") == "user":
                        text = _extract_text(msg)
                        return text.replace("\n", " ")[:120]
                except Exception:
                    continue
    except Exception:
        pass
    return ""


def make_bucket():
    return {
        "entries": 0,
        "cost": 0.0,
        "input": 0,
        "output": 0,
        "cacheRead": 0,
        "cacheWrite": 0,
    }


def add_to_bucket(b, inp, out, cr, cw, cost_val):
    b["entries"] += 1
    b["input"] += inp
    b["output"] += out
    b["cacheRead"] += cr
    b["cacheWrite"] += cw
    b["cost"] += cost_val


def bucket_to_dict(b):
    tokens = b["input"] + b["output"] + b["cacheRead"] + b["cacheWrite"]
    return {
        "entries": b["entries"],
        "cost": round(b["cost"], 2),
        "tokens": tokens,
        "tokens_fmt": fmt_tokens(tokens),
        "input": b["input"],
        "input_fmt": fmt_tokens(b["input"]),
        "output": b["output"],
        "output_fmt": fmt_tokens(b["output"]),
        "cacheRead": b["cacheRead"],
        "cacheRead_fmt": fmt_tokens(b["cacheRead"]),
        "cacheWrite": b["cacheWrite"],
        "cacheWrite_fmt": fmt_tokens(b["cacheWrite"]),
    }


def compute_range_stats(daily_list):
    if not daily_list:
        return {}

    days = len(daily_list)
    total_cost = sum(d["cost"] for d in daily_list)
    total_tokens = sum(d["tokens"] for d in daily_list)

    max_day = max(daily_list, key=lambda d: d["cost"])
    min_day = min(daily_list, key=lambda d: d["cost"])

    stats = {
        "days": days,
        "avgCost": round(total_cost / days, 2) if days else 0,
        "avgTokens": int(total_tokens / days) if days else 0,
        "avgTokens_fmt": fmt_tokens(int(total_tokens / days)) if days else "0",
        "maxCost": {"date": max_day["date"], "cost": max_day["cost"]},
        "minCost": {"date": min_day["date"], "cost": min_day["cost"]},
    }

    if days >= 2:
        last = daily_list[-1]
        prev = daily_list[-2]
        delta = round(last["cost"] - prev["cost"], 2)
        stats["lastDelta"] = {
            "from": prev["date"],
            "to": last["date"],
            "delta": delta,
            "pct": round((delta / prev["cost"] * 100), 1) if prev["cost"] > 0 else None,
        }

    return stats


def main():
    args = parse_args()

    # Determine date range
    if args.all:
        date_from, date_to = "0000-00-00", "9999-99-99"
    elif len(args.dates) == 2:
        date_from, date_to = args.dates[0], args.dates[1]
    elif len(args.dates) == 1:
        date_from = date_to = args.dates[0]
    else:
        yesterday = (
            datetime.datetime.now() - datetime.timedelta(days=1)
        ).strftime("%Y-%m-%d")
        date_from = date_to = yesterday

    is_range = date_from != date_to

    cost_map = load_cost_map()
    file_category, session_meta = build_session_classification()
    agents_dir = os.path.expanduser("~/.openclaw/agents")

    total = make_bucket()
    daily = defaultdict(make_bucket)  # date -> bucket

    cat_total = {}  # cat -> bucket + models
    model_total = defaultdict(make_bucket)  # mk -> bucket
    provider_total = defaultdict(make_bucket)  # provider -> bucket

    session_costs = defaultdict(
        lambda: {**make_bucket(), "model": "", "fpath": ""}
    )

    # Scan all sessions
    for agent in os.listdir(agents_dir):
        sessions_dir = os.path.join(agents_dir, agent, "sessions")
        if not os.path.isdir(sessions_dir):
            continue
        for fname in os.listdir(sessions_dir):
            if not fname.endswith(".jsonl"):
                continue
            cat = classify(fname, file_category)
            fpath = os.path.join(sessions_dir, fname)

            try:
                with open(fpath) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue

                        try:
                            entry = json.loads(line)
                        except Exception:
                            continue

                        ts = entry.get("timestamp", "")
                        if not date_matches(ts, date_from, date_to):
                            continue

                        msg = entry.get("message", {})
                        if not isinstance(msg, dict) or msg.get("role") != "assistant":
                            continue

                        usage = msg.get("usage") or entry.get("usage")
                        if not usage or not isinstance(usage, dict):
                            continue

                        provider = msg.get("provider", entry.get("provider", ""))
                        model_id = msg.get("model", entry.get("model", ""))
                        mk = f"{provider}/{model_id}" if provider else model_id

                        inp, out, cr, cw = extract_usage(usage)
                        cost_val = calc_cost(usage, mk, cost_map)
                        day = ts[:10]

                        add_to_bucket(total, inp, out, cr, cw, cost_val)
                        add_to_bucket(daily[day], inp, out, cr, cw, cost_val)

                        # Category
                        if cat not in cat_total:
                            cat_total[cat] = {
                                **make_bucket(),
                                "models": defaultdict(
                                    lambda: {"entries": 0, "cost": 0.0, "tokens": 0}
                                ),
                            }
                        add_to_bucket(cat_total[cat], inp, out, cr, cw, cost_val)
                        cat_total[cat]["models"][mk]["entries"] += 1
                        cat_total[cat]["models"][mk]["cost"] += cost_val
                        cat_total[cat]["models"][mk]["tokens"] += inp + out + cr + cw

                        # Model total
                        add_to_bucket(model_total[mk], inp, out, cr, cw, cost_val)

                        # Provider total
                        p, _ = split_model_key(mk)
                        add_to_bucket(provider_total[p], inp, out, cr, cw, cost_val)

                        # Session tracking (top-sessions)
                        if args.top_sessions > 0:
                            sk = (agent, fname)
                            add_to_bucket(session_costs[sk], inp, out, cr, cw, cost_val)
                            session_costs[sk]["model"] = mk
                            session_costs[sk]["fpath"] = fpath
            except Exception:
                pass

    # Build output
    output = {}

    if is_range:
        output["range"] = {"from": date_from, "to": date_to}
    else:
        output["date"] = date_from

    output["total"] = bucket_to_dict(total)

    total_cost = total["cost"]
    total_tokens = total["input"] + total["output"] + total["cacheRead"] + total["cacheWrite"]

    # Daily breakdown (only for range mode)
    if is_range:
        daily_list = []
        for day in sorted(daily.keys()):
            d = bucket_to_dict(daily[day])
            d["date"] = day
            daily_list.append(d)
        output["daily"] = daily_list
        output["stats"] = compute_range_stats(daily_list)

    # Categories
    output["categories"] = {}
    for cat_name in ["interactive", "cron", "heartbeat"]:
        c = cat_total.get(cat_name)
        if not c:
            continue
        c_dict = bucket_to_dict(c)
        c_tokens = c_dict["tokens"]
        output["categories"][cat_name] = {
            **c_dict,
            "pct_cost": round(c_dict["cost"] / total_cost * 100, 1) if total_cost > 0 else 0,
            "pct_tokens": round(c_tokens / total_tokens * 100, 1) if total_tokens > 0 else 0,
            "models": [
                {
                    "key": mk,
                    "name": display_model_key(mk),
                    "entries": md["entries"],
                    "cost": round(md["cost"], 2),
                    "tokens": md["tokens"],
                    "tokens_fmt": fmt_tokens(md["tokens"]),
                    "pct_cost": round(md["cost"] / total_cost * 100, 1) if total_cost > 0 else 0,
                    "pct_tokens": round(md["tokens"] / total_tokens * 100, 1) if total_tokens > 0 else 0,
                }
                for mk, md in sorted(c["models"].items(), key=lambda x: -x[1]["cost"])
                if "delivery-mirror" not in display_model_key(mk)
                and "acp-runtime" not in display_model_key(mk)
                and not (md["entries"] == 0 and md["cost"] == 0.0)
            ],
        }

    # Providers
    output["providers"] = []
    for p, b in sorted(provider_total.items(), key=lambda x: -x[1]["cost"]):
        p_short = short_provider(p)
        if p_short in ("delivery-mirror", "acp-runtime"):
            continue
        d = bucket_to_dict(b)
        output["providers"].append(
            {
                "provider": p,
                "name": p_short,
                **d,
                "pct_cost": round(d["cost"] / total_cost * 100, 1) if total_cost > 0 else 0,
                "pct_tokens": round(d["tokens"] / total_tokens * 100, 1) if total_tokens > 0 else 0,
            }
        )

    # Models
    output["models"] = []
    for mk, b in sorted(model_total.items(), key=lambda x: -x[1]["cost"]):
        name = display_model_key(mk)
        if "delivery-mirror" in name or "acp-runtime" in name:
            continue
        d = bucket_to_dict(b)
        output["models"].append(
            {
                "key": mk,
                "name": name,
                **d,
                "pct_cost": round(d["cost"] / total_cost * 100, 1) if total_cost > 0 else 0,
                "pct_tokens": round(d["tokens"] / total_tokens * 100, 1) if total_tokens > 0 else 0,
            }
        )

    # Top sessions
    if args.top_sessions > 0:
        top = sorted(session_costs.items(), key=lambda x: -x[1]["cost"])[: args.top_sessions]
        top_list = []
        for (agent, fname), b in top:
            if b["cost"] <= 0:
                continue
            basename = fname.replace(".jsonl", "")
            meta = session_meta.get(basename, {})
            cat = classify(fname, file_category)
            preview = get_first_user_message(b["fpath"])
            d = bucket_to_dict(b)
            top_list.append(
                {
                    "agent": agent,
                    "category": cat,
                    "session_key": meta.get("key", basename),
                    "preview": preview,
                    "model": display_model_key(b["model"]),
                    **d,
                    "pct_cost": round(d["cost"] / total_cost * 100, 1) if total_cost > 0 else 0,
                    "pct_tokens": round(d["tokens"] / total_tokens * 100, 1) if total_tokens > 0 else 0,
                }
            )
        output["topSessions"] = top_list

    # Output
    if args.format == "discord":
        text = format_discord(output, is_range)
        # Trend summary (discord only)
        if args.trend_days > 0 and not is_range:
            trend_text = _build_trend(args, date_from, cost_map, file_category, session_meta)
            if trend_text:
                text += "\n" + trend_text
        print(text)
    else:
        print(json.dumps(output, ensure_ascii=False, indent=2))


def _build_trend(args, target_day, cost_map, file_category, session_meta):
    """Build trend summary by scanning the last N days."""

    try:
        dt = datetime.datetime.strptime(target_day, "%Y-%m-%d")
    except ValueError:
        return ""

    dt_from = dt - datetime.timedelta(days=args.trend_days - 1)
    d_from = dt_from.strftime("%Y-%m-%d")
    d_to = target_day

    agents_dir = os.path.expanduser("~/.openclaw/agents")
    daily = defaultdict(make_bucket)

    for agent in os.listdir(agents_dir):
        sessions_dir = os.path.join(agents_dir, agent, "sessions")
        if not os.path.isdir(sessions_dir):
            continue
        for fname in os.listdir(sessions_dir):
            if not fname.endswith(".jsonl"):
                continue
            fpath = os.path.join(sessions_dir, fname)
            try:
                with open(fpath) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                        except Exception:
                            continue
                        ts = entry.get("timestamp", "")
                        if not date_matches(ts, d_from, d_to):
                            continue
                        msg = entry.get("message", {})
                        if not isinstance(msg, dict) or msg.get("role") != "assistant":
                            continue
                        usage = msg.get("usage") or entry.get("usage")
                        if not usage or not isinstance(usage, dict):
                            continue
                        provider = msg.get("provider", entry.get("provider", ""))
                        model_id = msg.get("model", entry.get("model", ""))
                        mk = f"{provider}/{model_id}" if provider else model_id
                        inp, out, cr, cw = extract_usage(usage)
                        cost_val = calc_cost(usage, mk, cost_map)
                        day = ts[:10]
                        add_to_bucket(daily[day], inp, out, cr, cw, cost_val)
            except Exception:
                pass

    if not daily:
        return ""

    daily_list = []
    for day in sorted(daily.keys()):
        d = bucket_to_dict(daily[day])
        d["date"] = day
        daily_list.append(d)

    stats = compute_range_stats(daily_list)
    if not stats:
        return ""

    today_cost = 0.0
    for d in daily_list:
        if d["date"] == target_day:
            today_cost = d["cost"]
            break

    lines = []
    lines.append(f"📈 趋势（近 {stats['days']} 天）")
    lines.append(f"  日均  ${stats['avgCost']} · {stats['avgTokens_fmt']} tokens")

    delta_avg = round(today_cost - stats["avgCost"], 2)
    sign_avg = "+" if delta_avg >= 0 else ""
    lines.append(f"  本日  ${today_cost}（较日均 {sign_avg}${delta_avg}）")

    if "lastDelta" in stats:
        ld = stats["lastDelta"]
        sign = "+" if ld["delta"] >= 0 else ""
        pct_str = f" {sign}{ld['pct']}%" if ld["pct"] is not None else ""
        lines.append(f"  较昨日  {sign}${ld['delta']}{pct_str}")

    lines.append(
        f"  峰值  {stats['maxCost']['date']} ${stats['maxCost']['cost']}"
        f" · 低谷  {stats['minCost']['date']} ${stats['minCost']['cost']}"
    )

    return "\n".join(lines)


def format_discord(output, is_range):
    """Format output dict as Discord-ready plain text."""

    lines = []

    # Header
    if is_range:
        r = output.get("range", {})
        lines.append(f"📊 {r.get('from', '?')} ~ {r.get('to', '?')} 费用报告")
    else:
        lines.append(f"💰 {output.get('date', '?')} 费用日报")

    lines.append("")

    # Total
    t = output["total"]
    lines.append("总计")
    lines.append(f"  费用   ${t['cost']}")
    lines.append(f"  调用   {t['entries']} 次")
    lines.append(f"  Token  {t['tokens_fmt']}")
    lines.append(f"    In {t['input_fmt']}  Out {t['output_fmt']}")
    lines.append(f"    Cache Read {t['cacheRead_fmt']}  Write {t['cacheWrite_fmt']}")

    # Range stats
    if is_range and "stats" in output:
        s = output["stats"]
        lines.append(f"  日均   ${s['avgCost']} · {s['avgTokens_fmt']} tokens")

    lines.append("")

    # Categories
    cat_labels = {
        "interactive": "💬 对话",
        "cron": "⏰ Cron",
        "heartbeat": "💓 心跳",
    }
    cats = output.get("categories", {})
    if cats:
        lines.append("分类")
        for cat_name in ["interactive", "cron", "heartbeat"]:
            c = cats.get(cat_name)
            if not c or c["entries"] == 0:
                continue
            label = cat_labels.get(cat_name, cat_name)
            lines.append(
                f"  {label}   ${c['cost']} ({c.get('pct_cost', 0)}%)"
                f"  {c['tokens_fmt']} ({c.get('pct_tokens', 0)}%)"
            )
        lines.append("")

    # Providers (all with cost > 0)
    providers = output.get("providers", [])
    visible_providers = [p for p in providers if p["cost"] > 0]
    if visible_providers:
        lines.append("供应商")
        for p in visible_providers:
            lines.append(
                f"  {p['name']}   ${p['cost']} ({p['pct_cost']}%)"
                f"  {p['tokens_fmt']} ({p['pct_tokens']}%)"
            )
        lines.append("")

    # Models (all with cost > 0)
    models = output.get("models", [])
    visible_models = [m for m in models if m["cost"] > 0]
    if visible_models:
        lines.append("模型")
        for m in visible_models:
            lines.append(
                f"  {m['name']}   ${m['cost']} ({m['pct_cost']}%)"
                f"  {m['tokens_fmt']} ({m['pct_tokens']}%)  {m['entries']} 次"
            )
            lines.append(
                f"    In {m['input_fmt']}  Out {m['output_fmt']}"
                f"  CR {m['cacheRead_fmt']}  CW {m['cacheWrite_fmt']}"
            )
        lines.append("")

    # Daily breakdown (range only)
    if is_range and "daily" in output:
        lines.append("逐日")
        for d in output["daily"]:
            lines.append(f"  {d['date']}  ${d['cost']}  {d['tokens_fmt']}")
        lines.append("")

        if "stats" in output:
            s = output["stats"]
            lines.append(
                f"  峰值  {s['maxCost']['date']} ${s['maxCost']['cost']}"
                f"  低谷  {s['minCost']['date']} ${s['minCost']['cost']}"
            )
            lines.append("")

    # Top sessions
    top = output.get("topSessions", [])
    if top:
        lines.append(f"🔥 最贵 Session Top {len(top)}")
        for i, s in enumerate(top, 1):
            lines.append(
                f"  {i}) [{s['category']}] {s['model']}"
                f"  ${s['cost']} ({s['pct_cost']}%)  {s['tokens_fmt']}  {s['entries']} 次"
            )
            if s.get("preview"):
                lines.append(f"     {s['preview'][:80]}")
        lines.append("")

    return "\n".join(lines).rstrip()


if __name__ == "__main__":
    main()
