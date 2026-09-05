#!/usr/bin/env python3
"""Render OpenClaw native session usage without depending on storage internals."""

import argparse
import datetime as dt
import json
import os
import sys
from decimal import Decimal, DecimalException, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from native_usage import Gateway, UsageError, acquire


def fmt_tokens(value):
    for unit, divisor in (("B", 10**9), ("M", 10**6), ("K", 10**3)):
        if value >= divisor:
            return f"{value / divisor:.2f}{unit}"
    return str(value)


def money(value):
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def previous_week(today):
    end = today - dt.timedelta(days=today.weekday() + 1)
    return (end - dt.timedelta(days=6)).isoformat(), end.isoformat()


def bucket(value, total=None):
    result = {k: int(value.get(k, 0)) for k in ("input", "output", "cacheRead", "cacheWrite")}
    for key in list(result):
        result[key + "_fmt"] = fmt_tokens(result[key])
    result.update(entries=value.get("count", 0), cost=money(value.get("totalCost", 0)),
                  tokens=value.get("totalTokens", 0), tokens_fmt=fmt_tokens(value.get("totalTokens", 0)))
    if total:
        result["pct_cost"] = round(float(value["totalCost"] / total["totalCost"] * 100), 1) if total["totalCost"] else 0
        result["pct_tokens"] = round(value["totalTokens"] / total["totalTokens"] * 100, 1) if total["totalTokens"] else 0
    return result


def project(data, top_count):
    dates, total = data["dateRange"], data["total"]
    result = {"date": dates["from"]} if dates["from"] == dates["to"] else {"range": dates}
    result.update(total=bucket(total), quality=data["quality"],
                  categories={k: bucket(v, total) for k, v in data["categories"].items()},
                  providers=[{"provider": k, "name": k, **bucket(v, total)}
                             for k, v in sorted(data["providers"].items(), key=lambda item: -item[1]["totalCost"])],
                  models=[{"key": "/".join(k), "name": "/".join(k), **bucket(v, total)}
                          for k, v in sorted(data["models"].items(), key=lambda item: -item[1]["totalCost"])])
    if "range" in result:
        result["daily"] = [{"date": d, "cost": money(v["cost"]), "entries": v["entries"],
                            "tokens": v["tokens"], "tokens_fmt": fmt_tokens(v["tokens"])}
                           for d, v in data["daily"].items()]
        days = list(data["daily"].items())
        high, low = max(days, key=lambda p: p[1]["cost"]), min(days, key=lambda p: p[1]["cost"])
        result["stats"] = {"days": len(days), "avgCost": money(total["totalCost"] / len(days)),
                           "avgTokens_fmt": fmt_tokens(total["totalTokens"] // len(days)),
                           "maxCost": {"date": high[0], "cost": money(high[1]["cost"])},
                           "minCost": {"date": low[0], "cost": money(low[1]["cost"])}}
    if top_count:
        result["topSessions"] = [{"agent": s["agent"], "category": s["category"],
                                  "session_key": s["session_key"], **bucket(s, total)}
                                 for s in sorted(data["top"], key=lambda x: -Decimal(str(x["totalCost"])))[:top_count]]
    return result


def format_discord(report):
    total = report["total"]
    period = report.get("date") or f"{report['range']['from']} ~ {report['range']['to']}"
    lines = [f"## 💰 {period} 费用报告"]
    quality = report["quality"]
    if quality["completeness"] != "complete":
        lines.append(f"数据不完整：{len(quality['unresolvedSessions'])} 个会话待核验，以下仅为已知用量。")
    if quality["pricingCompleteness"] != "complete":
        lines.append(f"价格不完整：{quality['missingCostEntries']} 条用量未计价。")
    lines += ["### 💵 总计", f"💲 估算费用 `${total['cost']:.2f}` · 🔢 用量记录 `{total['entries']}` 条 · 🪙 Token `{total['tokens_fmt']}`",
              f"-# In `{total['input_fmt']}` · Out `{total['output_fmt']}` · CR `{total['cacheRead_fmt']}` · CW `{total['cacheWrite_fmt']}`"]
    labels = {"interactive": "💬 对话", "cron": "⏰ Cron", "heartbeat": "💓 心跳", "system": "系统任务", "unknown": "未分类"}
    lines.append("### 📂 分类")
    for key, row in report["categories"].items():
        if row["tokens"] or row["cost"]:
            lines.append(f"{labels.get(key, key)}　`${row['cost']:.2f}` (`{row['pct_cost']}%`) · `{row['tokens_fmt']}`")
    for title, key in (("🏢 供应商", "providers"), ("🔮 模型", "models")):
        lines.append(f"### {title}")
        for row in report[key]:
            lines += [f"**{row['name']}**", f"`${row['cost']:.2f}` (`{row['pct_cost']}%`) · `{row['tokens_fmt']}` · `{row['entries']}` 条",
                      f"-# In `{row['input_fmt']}` · Out `{row['output_fmt']}` · CR `{row['cacheRead_fmt']}` · CW `{row['cacheWrite_fmt']}`"]
    if "daily" in report:
        lines.append("### 📅 逐日")
        lines.extend(f"{d['date']}　`${d['cost']:.2f}`　`{d['tokens_fmt']}`" for d in report["daily"])
    if "stats" in report:
        s = report["stats"]
        lines.append(f"日均 `${s['avgCost']:.2f}` · `{s['avgTokens_fmt']}`；峰值 {s['maxCost']['date']} `${s['maxCost']['cost']:.2f}`")
    for index, row in enumerate(report.get("topSessions", []), 1):
        lines.append(f"{index}. [{row['category']}] {row['agent']} `${row['cost']:.2f}` · `{row['tokens_fmt']}`")
    trend = report.get("trend")
    if trend:
        lines.append(f"### 近 {trend['stats']['days']} 天趋势")
        if trend["quality"]["completeness"] != "complete":
            lines.append("趋势数据不完整，仅统计已知用量。")
        s = trend["stats"]
        lines.append(f"日均 `${s['avgCost']:.2f}` · `{s['avgTokens_fmt']}`；峰值 {s['maxCost']['date']} `${s['maxCost']['cost']:.2f}`；低谷 {s['minCost']['date']} `${s['minCost']['cost']:.2f}`")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dates", nargs="*")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--previous-week", action="store_true")
    parser.add_argument("--format", choices=("json", "discord"), default="json")
    parser.add_argument("--top-sessions", type=int, default=0)
    parser.add_argument("--trend-days", type=int, default=0)
    args = parser.parse_args()
    if (len(args.dates) > 2 or (args.all and args.dates) or
            (args.previous_week and (args.all or args.dates)) or
            args.top_sessions < 0 or not 0 <= args.trend_days <= 366):
        parser.error("invalid report date/count options")
    zone = os.environ.get("OPENCLAW_USAGE_TIMEZONE", "Asia/Shanghai")
    try:
        today = dt.datetime.now(ZoneInfo(zone)).date()
        start = args.dates[0] if args.dates else (today - dt.timedelta(days=1)).isoformat()
        end = args.dates[-1] if args.dates else start
        if args.previous_week:
            start, end = previous_week(today)
        gateway = Gateway(budget=120)
        report = project(acquire(start, end, zone, gateway, args.all), args.top_sessions)
        if args.trend_days and "date" in report:
            trend_start = (dt.date.fromisoformat(start) - dt.timedelta(days=args.trend_days - 1)).isoformat()
            trend = project(acquire(trend_start, end, zone, gateway), 0)
            if "stats" not in trend:
                trend["stats"] = {"days": 1, "avgCost": trend["total"]["cost"],
                                  "avgTokens_fmt": trend["total"]["tokens_fmt"],
                                  "maxCost": {"date": start, "cost": trend["total"]["cost"]},
                                  "minCost": {"date": start, "cost": trend["total"]["cost"]}}
            report["trend"] = trend
        print(format_discord(report) if args.format == "discord" else json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if all(r["quality"]["completeness"] == "complete" and
                        r["quality"]["pricingCompleteness"] == "complete"
                        for r in [report, *([report["trend"]] if "trend" in report else [])]) else 2
    except (UsageError, ValueError, KeyError, TypeError, DecimalException) as exc:
        error = {"quality": {"source": "sessions.usage", "completeness": "unavailable"},
                 "error": str(exc) if isinstance(exc, UsageError) else "invalid report settings or native response"}
        print("费用统计不可用：" + error["error"] if args.format == "discord" else json.dumps(error, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
