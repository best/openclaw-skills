"""Native OpenClaw usage acquisition and date-scoped completeness checks."""

import datetime as dt
import json
import subprocess
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from zoneinfo import ZoneInfo

FIELDS = ("input", "output", "cacheRead", "cacheWrite", "totalTokens")
MIRRORS = {"delivery-mirror", "acp-runtime"}


class UsageError(Exception):
    pass


def number(value):
    if value is None:
        return Decimal(0)
    result = Decimal(str(value))
    if not result.is_finite() or result < 0:
        raise UsageError("invalid native usage number")
    return result


def empty():
    return {**dict.fromkeys(FIELDS, 0), "totalCost": Decimal(0), "count": 0,
            "missingCostEntries": 0}


def add(target, source, count=0):
    for key in FIELDS:
        value = number(source.get(key))
        if value != int(value):
            raise UsageError("non-integer token count")
        target[key] += int(value)
    target["totalCost"] += number(source.get("totalCost"))
    target["missingCostEntries"] += int(number(source.get("missingCostEntries")))
    target["count"] += int(number(count))


def close(left, right):
    return (all(number(left.get(k)) == number(right.get(k)) for k in FIELDS)
            and abs(number(left.get("totalCost")) - number(right.get("totalCost")))
            <= Decimal("0.000001"))


def identity(row):
    if not row.get("agentId") or not row.get("sessionId"):
        raise UsageError("native response omitted session identity")
    return row["agentId"], row["sessionId"]


def category(row):
    key = row.get("key", "")
    if "heartbeat" in key:
        return "heartbeat"
    if ":cron:" in key:
        return "cron"
    if any(x in key for x in (":subagent:", ":internal-", ":dreaming-")):
        return "system"
    if row.get("chatType") in ("direct", "group", "channel") or any(
            x in key for x in (":discord:", ":telegram:", ":feishu:", ":weixin:")):
        return "interactive"
    return "unknown"


class Gateway:
    def __init__(self, budget=120):
        self.deadline = time.monotonic() + budget

    def command(self, args):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise UsageError("native usage acquisition budget exhausted")
        try:
            proc = subprocess.run(["openclaw", *args], capture_output=True,
                                  text=True, timeout=min(35, remaining), check=False)
        except (OSError, subprocess.TimeoutExpired):
            raise UsageError("native usage CLI unavailable or timed out") from None
        if proc.returncode:
            raise UsageError("native usage CLI failed")
        try:
            result = json.loads(proc.stdout, parse_float=Decimal)
        except (ValueError, TypeError):
            raise UsageError("native usage response was not JSON") from None
        if not isinstance(result, dict) or result.get("ok") is False:
            raise UsageError("native usage request rejected")
        return result

    def usage(self, params):
        result = self.command(["gateway", "call", "sessions.usage", "--params",
                               json.dumps(params), "--json"])
        if not isinstance(result.get("sessions"), list) or not isinstance(
                result.get("totals"), dict):
            raise UsageError("native usage response schema changed")
        return result


def date_bounds(start, end, zone):
    tz = ZoneInfo(zone)
    first, last = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    if first > last:
        raise UsageError("start date must not follow end date")
    begin = dt.datetime.combine(first, dt.time(), tz)
    finish = dt.datetime.combine(last + dt.timedelta(days=1), dt.time(), tz)
    return int(begin.timestamp() * 1000), int(finish.timestamp() * 1000)


def acquire(start, end, zone, gateway=None, all_history=False):
    gateway = gateway or Gateway()
    params = {"agentScope": "all", "mode": "specific", "timeZone": zone,
              "groupBy": "instance", "includeContextWeight": False, "limit": 1000}
    if all_history:
        params["range"] = "all"
    else:
        date_bounds(start, end, zone)
        params.update(startDate=start, endDate=end)
    result = gateway.usage(params)
    while len(result["sessions"]) >= params["limit"]:
        if params["limit"] >= 32000:
            raise UsageError("native usage detail limit reached; refusing truncated report")
        params["limit"] *= 2
        result = gateway.usage(params)
    if all_history:
        start, end = result["startDate"], result["endDate"]
    begin_ms, finish_ms = date_bounds(start, end, zone)
    rows = result["sessions"]
    seen = set()
    initial = empty()
    for row in rows:
        ident = identity(row)
        if ident in seen:
            raise UsageError("duplicate native session instance")
        seen.add(ident)
        if row.get("usage"):
            add(initial, row["usage"])
    if not close(initial, result["totals"]):
        raise UsageError("native session details do not reconcile with totals")

    # Cross-check the public session inventory, not filenames or private tables.
    inventory = gateway.command(["sessions", "--all-agents", "--limit", "all", "--json"])
    if inventory.get("hasMore") or not isinstance(inventory.get("sessions"), list):
        raise UsageError("native session inventory is incomplete")
    for item in inventory["sessions"]:
        if not all_history and (item.get("updatedAt", 0) < begin_ms or
                (item.get("sessionStartedAt") or 0) >= finish_ms):
            continue
        ident = identity(item)
        if ident not in seen:
            seen.add(ident)
            rows.append({**item, "usage": None})

    def recover(row):
        lookup = {k: v for k, v in params.items() if k != "agentScope"}
        lookup.update(agentId=row["agentId"], key=row["key"], limit=1)
        for _ in range(3):
            try:
                fresh = gateway.usage(lookup)
            except UsageError:
                break
            match = next((s for s in fresh["sessions"]
                          if identity(s) == identity(row)), None)
            if match and match.get("usage") is not None:
                row["usage"] = match["usage"]
                return True
        return False

    missing = [row for row in rows if row.get("usage") is None]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(recover, missing))
    resolved = sum(results)
    unresolved = [{"agentId": row["agentId"], "sessionId": row["sessionId"]}
                  for row, success in zip(missing, results) if not success]
    return summarize(rows, start, end, zone, unresolved, resolved)


def summarize(rows, start, end, zone, unresolved=(), resolved=0):
    total = empty()
    models, providers, categories = (defaultdict(empty) for _ in range(3))
    daily = defaultdict(lambda: {"tokens": 0, "cost": Decimal(0), "entries": 0})
    top = []
    identity_set = set()
    for row in rows:
        ident = identity(row)
        if ident in identity_set:
            raise UsageError("duplicate native session instance")
        identity_set.add(ident)
        usage = row.get("usage")
        if usage is None:
            continue
        per_model = empty()
        count = 0
        for item in usage.get("modelUsage", []):
            value = item["totals"]
            if item.get("model") in MIRRORS:
                if number(value.get("totalTokens")) or number(value.get("totalCost")):
                    raise UsageError("nonzero usage on delivery mirror")
                continue
            provider = item.get("provider") or "unknown"
            model = item.get("model") or "unknown"
            calls = item.get("count", 0)
            add(per_model, value, calls)
            add(models[(provider, model)], value, calls)
            add(providers[provider], value, calls)
            count += int(number(calls))
        if not close(per_model, usage):
            raise UsageError("native model usage does not reconcile with session totals")
        add(total, usage, count)
        add(categories[category(row)], usage, count)
        session_daily_tokens = 0
        session_daily_cost = Decimal(0)
        for day in usage.get("dailyBreakdown", []):
            if not start <= day["date"] <= end:
                raise UsageError("native daily usage outside requested range")
            tokens = int(number(day["tokens"]))
            cost = number(day["cost"])
            daily[day["date"]]["tokens"] += tokens
            daily[day["date"]]["cost"] += cost
            session_daily_tokens += tokens
            session_daily_cost += cost
        if session_daily_tokens != int(number(usage.get("totalTokens"))) or abs(
                session_daily_cost - number(usage.get("totalCost"))) > Decimal("0.000001"):
            raise UsageError("native daily usage does not reconcile with session totals")
        for day in usage.get("dailyModelUsage", []):
            if day.get("model") not in MIRRORS:
                daily[day["date"]]["entries"] += int(number(day.get("count")))
        if number(usage.get("totalTokens")) or number(usage.get("totalCost")):
            top.append({"agent": row["agentId"], "category": category(row),
                        "session_key": row["key"], "sessionId": row["sessionId"],
                        **usage, "count": count})
    cursor, stop = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    if (stop - cursor).days > 4000:
        raise UsageError("report range exceeds 4000 days")
    while cursor <= stop:
        daily[cursor.isoformat()]
        cursor += dt.timedelta(days=1)
    return {"dateRange": {"from": start, "to": end}, "total": total,
            "models": models, "providers": providers, "categories": categories,
            "daily": dict(sorted(daily.items())), "top": top,
            "quality": {"source": "sessions.usage", "timeZone": zone,
                        "collectedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
                        "completeness": "partial" if unresolved else "complete",
                        "pricingCompleteness": "partial" if total["missingCostEntries"] else "complete",
                        "missingCostEntries": total["missingCostEntries"],
                        "unresolvedSessions": list(unresolved), "resolvedScopedSessions": resolved,
                        "sessionInstances": len(rows)}}
