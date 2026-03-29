---
name: discord-thread-archiver
version: 1.0.1
description: "Smart Discord thread archiving. Use when: (1) running periodic thread cleanup, (2) evaluating whether Discord threads should be archived. Agent lists active threads, reads messages, judges conversation status, archives resolved threads, and produces a structured report."
---

# Discord Thread Archiver

Scan active Discord threads, judge whether conversations have concluded, archive resolved ones, and produce a structured report.

## Parameters

The caller provides:
- `guildId` — Discord guild to scan
- `logChannel` — Channel ID for the report

## Workflow

### 1. List threads

Call `thread-list` exactly **once** with the provided `guildId`. This returns ALL active threads across every channel. Do NOT loop over channels.

```
message(action="thread-list", channel="discord", guildId="<guildId>")
```

If empty → send "⏸️ 无 Thread" report (see format below) and stop.

### 2. Evaluate each thread

Skip threads with `last_pin_timestamp` present → mark `skipped (pinned)`.

For all others, read the last 5 messages:
```
message(action="read", channel="discord", target="channel:<thread_id>", limit=5)
```

Apply judgment rules:
- **Bot-only lookback**: All 5 from bots → expand to limit=20 to check for earlier human participation
- **24h recency protection**: Last message within 24h → only archive with explicit closure signal
- **Classification**: Resolved with confirmation → archive; open/uncertain → keep

For detailed criteria, examples, and edge cases: read `references/judgment-guide.md`

### 3. Archive

For each thread judged **archive**, run the archive script:
```bash
bash <skill_dir>/scripts/archive-thread.sh <thread_id>
```
Pause 0.5s between calls. Non-2xx response → note in report (e.g. "403 权限不足").

### 4. Report

**When threads exist** (regardless of whether any were archived):
```
🗂️ Thread 归档 · HH:MM
✅ thread名 — 归档：一句话原因
⏸️ thread名 — 保留：一句话原因
⏭️ thread名 — 跳过(pinned)
归档 X / 保留 Y / 跳过 Z
```

**When thread-list returned empty**:
```
🗂️ Thread 归档 · HH:MM
⏸️ 无 Thread
```

Every evaluated thread MUST appear in the report with its verdict icon. Use only the icons that apply to each thread.

### 5. Deliver

Send the report:
```
message(action="send", channel="discord", target="channel:<logChannel>")
```
