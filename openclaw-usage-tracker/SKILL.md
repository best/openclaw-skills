---
name: openclaw-usage-tracker
description: >
  Track and report OpenClaw model usage and costs. Generate daily/weekly cost reports
  with per-model token breakdowns, interactive vs cron classification, and trend analysis.
  Use when: (1) user asks about model costs, usage, spending, or token consumption,
  (2) setting up automated daily/weekly cost reports via cron,
  (3) analyzing which models or sessions consume the most tokens/money,
  (4) comparing interactive chat vs cron job costs.
---

# OpenClaw Usage Tracker

Scan OpenClaw session transcripts (.jsonl) to report model usage and estimated costs.

## How It Works

Each assistant message in `~/.openclaw/agents/<agent>/sessions/*.jsonl` carries a
`usage` object (input, output, cache_read, cache_write tokens). Cost comes from the
API response or is estimated via per-model pricing in `openclaw.json`.

## Usage

```bash
# Yesterday (default)
python3 scripts/daily-cost-report.py

# Specific date
python3 scripts/daily-cost-report.py 2026-03-14
```

Output is JSON with `date`, `total`, `categories` (interactive/cron/heartbeat), and
`models` (per-model breakdown). Parse and format for the target channel.

## Discord Output Format

```
💰 {date} 费用日报

总计: ${cost} | {entries}次调用 | {tokens_fmt} tokens
  Input: {input_fmt} | Output: {output_fmt}
  Cache Read: {cacheRead_fmt} | Cache Write: {cacheWrite_fmt}

💬 对话: {entries}次 | {tokens_fmt} | ${cost} ({pct}%)
  {model}: {entries}次 ${cost}
⏰ Cron: {entries}次 | {tokens_fmt} | ${cost} ({pct}%)
  {model}: {entries}次 ${cost}

📋 模型汇总:
  {model}: {entries}次 | {tokens_fmt} | ${cost}
```

Skip categories with 0 entries. Skip models with $0.00 cost and 0 entries.

## Daily Cron Setup

Create an isolated cron job (00:05 Asia/Shanghai, cost-effective model like sonnet,
delivery=none since the agent sends via message tool). Prompt template:

```
执行每日费用账单推送。
1. 运行脚本：python3 <skill_dir>/scripts/daily-cost-report.py
2. 解析 JSON 输出，按 SKILL.md 格式模板格式化
3. 用 message 工具发送到目标 Discord 频道
跳过费用 $0 且调用 0 的模型，跳过无数据的分类。
```

## Session Classification

1. **Session key** — `cron:` → cron, `heartbeat` → heartbeat, else → interactive
2. **Content fallback** — orphaned sessions checked for `[cron:...]` prefix in first user message

## Cost Calculation

1. Provider-returned `usage.cost.total` (priority)
2. Estimated: `(input × cost.input + output × cost.output + cacheRead × cost.cacheRead + cacheWrite × cost.cacheWrite) / 1M`

Pricing: `models.providers.<provider>.models[].cost` in `openclaw.json` ($/M tokens).

## Notes

- Scans all agent directories (`~/.openclaw/agents/*/sessions/`)
- Filters out `delivery-mirror` and `acp-runtime` (no real token usage)
- Cache Read typically dominates total tokens (80%+) due to prompt caching
