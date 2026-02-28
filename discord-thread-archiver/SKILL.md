---
name: discord-thread-archiver
description: "Smart Discord thread archiving with AI conversation analysis. Use when: (1) periodically cleaning up inactive threads, (2) setting up automated thread lifecycle management, (3) analyzing whether Discord conversations have concluded. Requires DISCORD_BOT_TOKEN env var. Supports AI-powered conversation completion detection via Anthropic-compatible API."
---

# Discord Thread Archiver

Archive inactive Discord threads using AI to judge whether conversations have concluded.

## Usage

```bash
python3 scripts/archiver.py [--dry-run] [--verbose]
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| DISCORD_BOT_TOKEN | Yes | Discord Bot token (falls back to OpenClaw config) |
| ARCHIVER_GUILD_ID | No | Guild ID (default: from script) |
| ARCHIVER_AI_BASE_URL | No | Anthropic-compatible API base URL (falls back to OpenClaw config) |
| ARCHIVER_AI_API_KEY | No | API key for AI provider (falls back to OpenClaw config) |
| ARCHIVER_AI_MODEL | No | Model ID (default: claude-sonnet-4-6) |

## Decision Flow

```
Thread enters evaluation
  ├─ Has pin → never archive
  ├─ < 2h inactive → skip
  ├─ Bot-only messages + 4h → archive
  ├─ 4h+ inactive → AI reads last 8 messages
  │   ├─ concluded → archive
  │   ├─ ongoing → lenient threshold (tier × 1.5)
  │   └─ uncertain → fall through
  └─ Time-based fallback
      ├─ 1-3 msgs → 8h
      ├─ 4-20 msgs → 24h
      └─ 20+ msgs → 48h
```

## Output

Human-readable log + final JSON line:

```json
{"archived": 2, "kept": 3, "failed": 0, "ai_calls": 4, "details": [...]}
```

## Notes

- Skill handles archiving logic only — scheduling and delivery are the caller's responsibility
- Bot needs `MANAGE_THREADS` permission in the Discord guild
- AI judgment uses `max_tokens: 20` per call — negligible cost
