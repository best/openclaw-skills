---
name: usage-tracker
description: >
  Track and report OpenClaw model usage and costs. Generate daily/weekly cost reports
  with per-model token breakdowns, interactive vs cron classification, and trend analysis.
  Use when: (1) user asks about model costs, usage, spending, or token consumption,
  (2) setting up automated daily/weekly cost reports via cron,
  (3) analyzing which models or sessions consume the most tokens/money,
  (4) comparing interactive chat vs cron job costs.
---

# Usage Tracker

Track OpenClaw model usage costs by scanning session transcript files (.jsonl) and
estimating costs from configured model pricing.

## How It Works

OpenClaw stores every LLM interaction in `.jsonl` transcript files under
`~/.openclaw/agents/<agent>/sessions/`. Each assistant message includes a `usage`
object with token counts (input, output, cache_read, cache_write). Cost is either
provided by the API response or estimated using per-model pricing from `openclaw.json`.

## Quick Commands

### Ad-hoc Report (specific date)

```bash
python3 scripts/daily-cost-report.py 2026-03-14
```

### Yesterday's Report (default)

```bash
python3 scripts/daily-cost-report.py
```

Output is JSON. Parse it and format for the target channel.

## Output Schema

The script outputs JSON with:
- `date` — target date
- `total` — aggregate: cost, entries, tokens (with formatted strings)
- `categories` — breakdown by `interactive` / `cron` / `heartbeat`, each with model list
- `models` — per-model totals with full token breakdown

## Formatting for Discord

Format the JSON output as:

```
💰 {date} 费用日报

总计: ${cost} | {entries}次调用 | {tokens_fmt} tokens
  Input: {input_fmt} | Output: {output_fmt}
  Cache Read: {cacheRead_fmt} | Cache Write: {cacheWrite_fmt}

💬 对话: {entries}次 | {tokens_fmt} | ${cost} ({pct}%)
  {model}: {entries}次 ${cost}
  ...
⏰ Cron: {entries}次 | {tokens_fmt} | ${cost} ({pct}%)
  {model}: {entries}次 ${cost}
  ...

📋 模型汇总:
  {model}: {entries}次 | {tokens_fmt} | ${cost}
  ...
```

Skip categories with 0 entries. Skip models with $0.00 cost and 0 entries.

## Setting Up Daily Cron

Create an isolated cron job. See `references/cron-setup.md` for the recommended
cron configuration and prompt template.

## Session Classification

Sessions are classified by:
1. **Session key** — `cron:` prefix → cron, `heartbeat` → heartbeat, else → interactive
2. **Content fallback** — orphaned sessions (not in sessions.json) are checked for
   `[cron:...]` prefix in the first user message

## Cost Calculation

Priority order:
1. Provider-returned `usage.cost.total` (from API response)
2. Estimated: `(input × cost.input + output × cost.output + cacheRead × cost.cacheRead + cacheWrite × cost.cacheWrite) / 1M`

Pricing config: `models.providers.<provider>.models[].cost` in `openclaw.json`.
Unit: dollars per million tokens.

## Notes

- The script scans ALL agent directories (`~/.openclaw/agents/*/sessions/`)
- `delivery-mirror` and `acp-runtime` entries are filtered out (no real token usage)
- Cache Read typically dominates total tokens (80%+) due to Anthropic prompt caching
- Cost estimation accuracy depends on correct pricing in `openclaw.json`
