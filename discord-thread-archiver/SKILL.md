---
name: discord-thread-archiver
version: 0.3.0
description: "Smart Discord thread archiving. Use when: (1) running periodic thread cleanup, (2) evaluating whether Discord threads should be archived. Agent reads thread messages, judges conversation status, and archives concluded threads."
---

# Discord Thread Archiver

Evaluate active threads and archive concluded conversations. AI judgment is the primary decision mechanism — time alone is never sufficient reason to archive.

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
| Safety net | 7d+ inactive (any thread) | Archive |
| **AI judgment** | 2h+ inactive → read last 10 messages | See below |

Inactive time = now − `thread_metadata.archive_timestamp`.

### 3. AI judgment (primary mechanism)

Read messages:
```
message(action="read", channel="discord", target="channel:<thread_id>", limit=10)
```

Evaluate conversation state and classify:

| Verdict | Criteria | Action |
|---------|----------|--------|
| **Concluded** | Clear resolution: thanks/confirmation, question answered, task completed, mutual agreement reached | Archive |
| **Ongoing** | Open question unanswered, debate in progress, action items pending, waiting for someone | **Keep** |
| **Uncertain** | Can't tell from context | **Keep** (default to preserving) |

Key principle: **When in doubt, keep the thread.** A user not responding does not mean the conversation is over — they may return later. Only archive when there are clear signals of conclusion.

### 4. Archive

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

### 5. Report

Summarize: archived count, kept count, reasons. One line per archived thread.

## Requirements

- Bot needs `MANAGE_THREADS` permission
- Scheduling and result delivery are the caller's responsibility
