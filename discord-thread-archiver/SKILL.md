---
name: discord-thread-archiver
version: 0.5.0
description: "Smart Discord thread archiving. Use when: (1) running periodic thread cleanup, (2) evaluating whether Discord threads should be archived. Agent reads thread messages, judges conversation status, and archives concluded threads."
---

# Discord Thread Archiver

Evaluate active threads and archive concluded conversations. AI judgment is the sole decision mechanism — time is context, not criteria.

## Procedure

### 1. List threads (ONE call per guild)

Call `thread-list` exactly **once** with `guildId`. This returns ALL active threads across every channel in the guild. Do NOT loop over channels — that produces duplicate data and wastes tokens.

```
message(action="thread-list", channel="discord", guildId="<guild>")
```

### 2. Skip pinned threads

Only skip threads with `last_pin_timestamp` present — these are explicitly marked for retention.

All other threads proceed to AI judgment.

### 3. AI judgment — read messages and decide

For every non-pinned thread, read the last 5 messages:

```
message(action="read", channel="discord", target="channel:<thread_id>", limit=5)
```

Classify the conversation:

| Verdict | Criteria | Action |
|---------|----------|--------|
| **Concluded** | Clear resolution: thanks/confirmation, question answered, task completed, explicit "done"/"结束", or notification consumed with no follow-up needed | Archive |
| **Bot-only** | All messages from bots, no human participation | Archive |
| **Ongoing** | Open question unanswered, action items pending, waiting for response, active discussion | **Keep** |
| **Uncertain** | Can't determine from 5 messages | **Keep** |

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

**When threads were archived:**
```
🗂️ Thread 归档报告 · YYYY-MM-DD HH:MM

✅ <thread_name> — 归档：<brief reason based on message content>
⏸️ <thread_name> — 保留：<brief reason, e.g. 最后 5 条消息显示仍有未回答的问题>
⏭️ <thread_name> — 跳过(pinned)

归档 X / 保留 Y / 跳过(pinned) Z
```

**When no threads need archiving:**
```
🗂️ Thread 归档报告 · YYYY-MM-DD HH:MM

无需归档的 Thread
⏸️ <thread_name> — 保留：<brief reason>
⏭️ <thread_name> — 跳过(pinned)

归档 0 / 保留 X / 跳过(pinned) Y
```

**Report rules:**
- Every thread must appear in the report with its verdict and reason
- Reasons should reference what was observed in the messages (e.g. "最后 5 条消息显示对话停在开放问题上")
- Do NOT include internal implementation details (API calls, curl commands, constraints) in the report

## Token Optimization Rules

1. **ONE thread-list call per guild** — never per-channel
2. **limit=5** for message reads — last 5 messages is sufficient for judgment
3. Only pinned threads skip message reading; all others are evaluated
