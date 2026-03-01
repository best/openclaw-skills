---
name: discord-thread-archiver
version: 0.4.0
description: "Smart Discord thread archiving. Use when: (1) running periodic thread cleanup, (2) evaluating whether Discord threads should be archived. Agent reads thread messages, judges conversation status, and archives concluded threads."
---

# Discord Thread Archiver

Evaluate active threads and archive concluded conversations. AI judgment is the primary decision mechanism — time alone is never sufficient reason to archive.

## Procedure

### 1. List threads (ONE call per guild)

Call `thread-list` exactly **once** with `guildId`. This returns ALL active threads across every channel in the guild. Do NOT loop over channels — that produces duplicate data and wastes tokens.

```
message(action="thread-list", channel="discord", guildId="<guild>")
```

### 2. Filter — skip before reading messages

Apply these rules first (no message reading needed):

| Rule | Condition | Action |
|------|-----------|--------|
| Pinned | `last_pin_timestamp` exists | Skip |
| Too fresh | < 2h since last message | Skip |

Inactive time = `now − last_message_timestamp`. If unavailable, use `archive_timestamp` from `thread_metadata`.

### 3. AI judgment — read messages only for candidates

For threads that pass the filter (2h+ inactive), read the last 10 messages:

```
message(action="read", channel="discord", target="channel:<thread_id>", limit=10)
```

Classify the conversation:

| Verdict | Criteria | Action |
|---------|----------|--------|
| **Concluded** | Clear resolution: thanks/confirmation, question answered, task completed, explicit "done"/"结束" | Archive |
| **Bot-only** | All messages from bots + 4h inactive | Archive |
| **Safety net** | 7d+ inactive regardless of content | Archive |
| **Ongoing** | Open question unanswered, action items pending, waiting for response | **Keep** |
| **Uncertain** | Can't determine from context | **Keep** |

**When in doubt, keep the thread.** A user not responding ≠ conversation over.

### 4. Archive via Discord API (curl)

`channel-edit` cannot set `archived` — you MUST use curl:

```bash
BOT_TOKEN=$(python3 -c "import json; print(json.load(open('/root/.openclaw/openclaw.json'))['channels']['discord']['token'])")

curl -s -o /dev/null -w "%{http_code}" -X PATCH \
  -H "Authorization: Bot $BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -H "User-Agent: DiscordBot (https://openclaw.ai, 1.0)" \
  -d '{"archived": true}' \
  "https://discord.com/api/v10/channels/<thread_id>"
```

- Expected response: `200` = success
- Sleep 0.5s between archive calls (rate limit)
- If you get `403`, the bot lacks `MANAGE_THREADS` permission — report this in the summary, do NOT silently skip

### 5. Report

Send a summary to the designated channel. Format:

```
🗂️ Thread 归档报告 · YYYY-MM-DD HH:MM
- ✅ <thread_name> — <reason>
- ⏸️ <thread_name> — <reason>
归档 X / 保留 Y / 跳过 Z
```

## Token Optimization Rules

1. **ONE thread-list call per guild** — never per-channel
2. **Skip before read** — filter by time first, only read messages for 2h+ inactive threads
3. **limit=10** for message reads — don't fetch entire thread history

## Requirements

- Bot needs `MANAGE_THREADS` permission in target channels
- Scheduling and result delivery are the caller's responsibility
