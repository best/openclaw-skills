---
name: openclaw-usage-tracker
description: >
  Track and report OpenClaw model usage and costs. Generate daily/weekly cost reports
  with per-model token breakdowns, interactive vs cron classification, provider summary,
  and trend analysis.
metadata:
  version: 1.2.0
---

# OpenClaw Usage Tracker

Scan OpenClaw session transcripts (`*.jsonl`) to report token usage and estimated costs.

## How It Works

Each assistant message in `~/.openclaw/agents/<agent>/sessions/*.jsonl` carries a
`usage` object (input, output, cache read, cache write). Cost comes from the provider
API response (`usage.cost.total`) or is estimated via per-model pricing in `openclaw.json`.

## Usage

```bash
# Yesterday (default)
python3 scripts/daily-cost-report.py

# Specific date
python3 scripts/daily-cost-report.py 2026-03-14

# Date range (逐日明细 + 汇总)
python3 scripts/daily-cost-report.py 2026-03-10 2026-03-15

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

`total` / each daily entry / each provider / each model / each topSession includes:
- `cost`, `entries`, `tokens`/`tokens_fmt`
- `input`/`input_fmt`, `output`/`output_fmt`, `cacheRead`/`cacheRead_fmt`, `cacheWrite`/`cacheWrite_fmt`
- `pct_cost`, `pct_tokens` (share within the report scope)

`models[]` uses a display-safe `name` that includes provider + model:
- Example: `astralor/Opus-4.6`, `gptclub/GPT-5.4`, `minimax/M2.5`

## Daily Report Template (Discord)

Goal: clear view (token + money), not maximum density.

```
💰 {date} 费用日报

总计
  费用  ${total.cost}
  调用  {total.entries} 次
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

Recommended: isolated cron, delivery=none (agent sends via `message` tool).

Daily job should generate a report for **yesterday** plus a short 7-day trend summary:

- Run once for yesterday (no args) → build the main report
- Run once for last 7 days (yesterday-6 .. yesterday) → compute avg/max/min + deltas

## Session Classification

1. **Session key** — `cron:` → cron, `heartbeat` → heartbeat, else → interactive
2. **Content fallback** — orphaned sessions checked for `[cron:...]` prefix in the first user message

## Cost Calculation

1. Provider-returned `usage.cost.total` (priority)
2. Estimated: `(input × cost.input + output × cost.output + cacheRead × cost.cacheRead + cacheWrite × cost.cacheWrite) / 1M`

Pricing: `models.providers.<provider>.models[].cost` in `openclaw.json` ($/M tokens).

## Notes

- Scans all agent directories (`~/.openclaw/agents/*/sessions/`)
- Filters out `delivery-mirror` and `acp-runtime` in display output
- Cache Read typically dominates total tokens due to prompt caching
