---
name: discord-thread-archiver
description: "Smart Discord thread archiving. Use when: (1) running periodic thread cleanup, (2) evaluating whether Discord threads should be archived. Agent lists active threads, reads messages, judges conversation status, archives resolved threads, and produces a structured report."
metadata:
  version: 1.1.1
---

# Discord Thread Archiver

Scan active Discord threads, judge whether conversations have concluded, archive resolved ones, and produce a structured report.

## Parameters

The caller provides:
- `guildId` — Discord guild to scan
- `logChannel` — Channel ID for the report

## Workflow

### 1. List threads

Call `thread-list` exactly **once** with both `guildId` and `channelId`. This returns active threads **only under the specified parent channel**. Do NOT call without `channelId` — never scan the entire guild.

```
message(action="thread-list", channel="discord", guildId="<guildId>", channelId="<channelId>")
```

If empty → send "⏸️ 无 Thread" report (see format below) and stop.

### 2. Load judgment rules

Read the full judgment guide before evaluating any thread:
```
read("references/judgment-guide.md")
```

### 3. Evaluate each thread

Skip threads with `last_pin_timestamp` present → mark `skipped (pinned)`.

For all others, read the last 5 messages:
```
message(action="read", channel="discord", target="channel:<thread_id>", limit=5)
```

#### 3a. Bot-only lookback

All 5 messages from bots → expand to limit=20 to find earlier human participation.

#### 3b. Hard gate checks

Apply these mechanical checks first. If ANY gate triggers → verdict is **keep**, skip classification.

| # | Condition | Verdict |
|---|-----------|---------|
| G1 | Last message from bot AND contains "？" or "吗" or ends with question | **keep** — 等待回复 |
| G2 | Last message < 24h old AND no human closure signal found | **keep** — 近期无关闭 |
| G3 | Human-bot collaboration (lookback found human messages) AND < 24h | **keep** — 协作中 |

**Closure signals** (must come from a human, not bot): 好了, 搞定, done, 结束, 谢谢, thanks, 确认, 没问题, OK, 可以了

#### 3c. Classify

Only threads that pass ALL hard gates reach this step. Apply the classification table from the judgment guide.

**Key rule:** "task completed" = entire discussion resolved with human acknowledgment, not a single sub-step done. If the thread has multiple topics and any is unresolved → **keep**.

### 4. Archive

For each thread judged **archive**, run the archive script:
```bash
bash <skill_dir>/scripts/archive-thread.sh <thread_id>
```
Pause 0.5s between calls. Non-2xx response → note in report (e.g. "403 权限不足").

### 5. Report

**Icon-verdict mapping (STRICT — never mix these up):**
| Icon | Verdict | Meaning |
|------|---------|---------|
| ✅ | archive | Thread was archived |
| ⏸️ | keep | Thread is kept (NOT ✅) |
| ⏭️ | skip | Thread is pinned, skipped |

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

### 6. Deliver

Send the report:
```
message(action="send", channel="discord", target="channel:<logChannel>")
```
