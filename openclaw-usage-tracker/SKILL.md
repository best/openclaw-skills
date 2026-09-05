---
name: "openclaw-usage-tracker"
description: "Native OpenClaw daily and weekly usage reports with explicit completeness and missing-price checks."
metadata:
  version: 1.4.2
---

# OpenClaw Usage Tracker

Query OpenClaw's native `sessions.usage` API to report token usage and estimated costs.
Report dates use the Asia/Shanghai local day by default; override with
`OPENCLAW_USAGE_TIMEZONE=<IANA timezone>` when needed.

## How It Works

Use the public Gateway API plus the public session inventory, including SQLite-backed and retained archived sessions. Refresh cold native lists in bounded batches before querying remaining same-identity gaps. Unresolved entries retain their failure reason and are reported as partial, never as zero spending. Token/model/day aggregates must reconcile before a report is accepted. No direct database reads or filesystem transcript scans are used.

## Usage

```bash
# Yesterday (default)
python3 scripts/daily-cost-report.py

# Specific date
python3 scripts/daily-cost-report.py 2026-03-14

# Date range (逐日明细 + 汇总)
python3 scripts/daily-cost-report.py 2026-03-10 2026-03-15

# Completed previous Monday-Sunday (local report timezone)
python3 scripts/daily-cost-report.py --previous-week --top-sessions 5 --format discord

# All history
python3 scripts/daily-cost-report.py --all

# Include top N most expensive sessions
python3 scripts/daily-cost-report.py 2026-03-14 --top-sessions 10

# Combine: range + top sessions
python3 scripts/daily-cost-report.py --all --top-sessions 5
```

## Output Schema

JSON output. Structure adapts to mode:

- **Single day** → `{date, total, categories, providers, models, topSessions?}`
- **Range/all** → `{range: {from, to}, total, daily: [{date, ...}], stats, categories, providers, models, topSessions?}`

`total`, providers, models, categories and top sessions include `cost`, `entries`, `tokens`, and input/output/cache counters with formatted values. `entries` counts native usage-bearing records, excluding zero-use delivery mirrors; it is not an upstream billing-request count.

Range `daily` entries include date, cost, tokens and entries; token-type breakdowns are not invented when the native daily API does not provide them. `quality` records the source, time zone, collection time, data completeness, pricing completeness, unresolved sessions and scoped repairs. Exit 0 means complete data and pricing, 2 means partial data or pricing, and 1 means unavailable/invalid. Preserve the stdout status report even on nonzero exit.

`models[]` uses a display-safe `name` that includes provider + model:
- Example: `provider-a/model-a`, `provider-b/model-b`

## Daily Report Template (Discord)

Goal: clear view (token + money), not maximum density.

```
💰 {date} 费用日报

总计
  费用  ${total.cost}
  用量记录  {total.entries} 条
  Token {total.tokens_fmt}
    In {total.input_fmt} · Out {total.output_fmt}
    Cache Read {total.cacheRead_fmt} · Write {total.cacheWrite_fmt}

分类
  💬 对话   ${interactive.cost} ({interactive.pct_cost}%) · {interactive.tokens_fmt} ({interactive.pct_tokens}%)
  ⏰ Cron   ${cron.cost} ({cron.pct_cost}%) · {cron.tokens_fmt} ({cron.pct_tokens}%)
  💓 心跳   ${heartbeat.cost} ({heartbeat.pct_cost}%) · {heartbeat.tokens_fmt} ({heartbeat.pct_tokens}%)

供应商（按费用）
  {provider.name}  ${provider.cost} ({provider.pct_cost}%) · {provider.tokens_fmt} ({provider.pct_tokens}%)

模型（按费用）
  {model.name}  ${model.cost} ({model.pct_cost}%) · {model.tokens_fmt} ({model.pct_tokens}%) · {model.entries} 次
    In {model.input_fmt} · Out {model.output_fmt} · CR {model.cacheRead_fmt} · CW {model.cacheWrite_fmt}

趋势（近 7 天）
  日均 ${avg_cost} · {avg_tokens}
  本日 ${today_cost}（较日均 {delta_vs_avg}，较昨日 {delta_vs_prev}）
  峰值 {max_day} ${max_cost} · 低谷 {min_day} ${min_cost}
```

Skip categories with 0 entries. Skip models/providers with `$0.00` and 0 entries.

## Daily Cron Setup

Use exactly one delivery owner. Existing agent-turn jobs may retain delivery=none and forward the complete script stdout, including partial/unavailable notices. A later command migration may use native announce only after removing explicit sends.

Daily job should generate a report for **yesterday** plus a short 7-day trend summary:

- Run once for yesterday (no args) → build the main report
- Run once for last 7 days (yesterday-6 .. yesterday) → compute avg/max/min + deltas

## Session Classification

Use native session identity and channel metadata. Recognized Cron and heartbeat keys keep their categories; internal/subagent keys are system tasks. Archived records without authoritative category metadata remain `unknown`. Do not infer a category from message counts or invent one to make totals look complete.

## Cost Calculation

Use the native API's cost and missing-price markers. Keep estimates separate from actual supplier charges and subscription quotas. A missing price is not free usage. Do not fail over to `usage.cost` or add its output to `sessions.usage`.

## Verification

Run `python3 -m unittest discover -s scripts -p 'test_native_usage.py'`. Compare a fixed completed local day, a seven-day range and upgrade-spanning dates. Preserve native instance identities; do not sum family and instance results. Report partial coverage or unknown classification visibly.

The acquisition budget is 120 seconds for the report and optional trend combined. Batch refresh runs at most three times; remaining same-identity queries use up to 12 workers and three full passes, retrying only not-ready results. Preserve known usage and explicit unresolved reasons when the budget expires. Invoke with Python 3.9+ and the authenticated local OpenClaw CLI; do not pass credentials in arguments or print CLI diagnostic output.
