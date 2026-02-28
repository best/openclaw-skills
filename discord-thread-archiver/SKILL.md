---
name: discord-thread-archiver
version: 2.0.0
description: "Smart Discord thread archiving. Use when: (1) running periodic thread cleanup, (2) evaluating whether Discord threads should be archived. Agent reads thread messages, judges conversation status, and archives concluded threads."
---

# Discord Thread Archiver

Evaluate active threads and archive concluded conversations. You ARE the judge — read messages and decide.

## Procedure

### 1. List threads

```
message(action="thread-list", channel="discord", channelId="<parent_channel>", guildId="<guild>")
```

### 2. Evaluate each thread

Apply in order, stop at first match:

| Rule | Condition | Action |
|------|-----------|--------|
| Pinned | `last_pin_timestamp` exists | Skip |
| Too fresh | < 2h inactive | Skip |
| Bot-only | All messages from bots + 4h inactive | Archive |
| **Your judgment** | 4h+ inactive → read last 8 messages | Concluded → archive / Ongoing → lenient / Uncertain → time rule |
| Time fallback | 1-3 msgs: 8h / 4-20 msgs: 24h / 20+: 48h | Archive if exceeded |

Read messages for judgment:
```
message(action="read", channel="discord", target="channel:<thread_id>", limit=8)
```

Inactive time = now − `thread_metadata.archive_timestamp`.

"Lenient" for ongoing = tier hours × 1.5.

### 3. Archive

`channel-edit` cannot set `archived` (schema limitation). Use exec:

```bash
curl -s -o /dev/null -w "%{http_code}" -X PATCH \
  -H "Authorization: Bot $(python3 -c \"import json; print(json.load(open('/root/.openclaw/openclaw.json'))['channels']['discord']['token'])\")" \
  -H "Content-Type: application/json" \
  -H "User-Agent: DiscordBot (https://openclaw.ai, 1.0)" \
  -d '{"archived": true}' \
  "https://discord.com/api/v10/channels/<thread_id>"
```

Sleep 0.5s between calls (rate limit).

### 4. Report

Summarize: archived count, kept count, reasons. One line per archived thread.

## Requirements

- Bot needs `MANAGE_THREADS` permission
- Scheduling and result delivery are the caller's responsibility
