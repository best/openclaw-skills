---
name: "discord-thread-archiver"
description: "Archive resolved Discord threads with deterministic history collection, classification, and reporting."
metadata:
  version: 1.3.3
---

# Discord Thread Archiver

Scan active Discord threads, collect trustworthy participation facts, classify each thread, archive resolved threads, and report every decision.

## Parameters

- `guildId` — Guild to scan
- `channelId` — Parent channel to scan
- `logChannel` — Report channel
- `operationalThreadPrefixes` — Optional comma-separated prefixes; default `🤖 `
- `mode` — `apply` (default) or `dry-run`

## Workflow

### 1. List once

Call `thread-list` exactly once with both `guildId` and `channelId`:

```
message(action="thread-list", channel="discord", guildId="<guildId>", channelId="<channelId>")
```

Never scan the whole guild. If empty, deliver the no-thread report and stop.

### 2. Load rules

Read `references/judgment-guide.md` in full before evaluating threads.

### 3. Evaluate

Skip pinned threads and report `skip/pinned`.

#### 3a. Latest window and hard gate

Read the latest five messages exactly once:

```
message(action="read", channel="discord", target="channel:<thread_id>", limit=5)
```

Determine the latest message by timestamp or numeric Discord ID; provider array order is not a facts contract.

If the latest message is a bot question, return `keep/bot_question_unanswered` immediately. Do not paginate or call the classifier.

#### 3b. Deterministic historical lookback

If the five-message window contains a human, participation collection is complete.

If all five are bots, read the latest 20 messages exactly once with no cursor. Never repeat this no-cursor window.

Inspect the thread starter and its `referenced_message`. A bot-authored type-21 starter with `referenced_message.author.bot=false` is human-initiated. Record `humanInitiated=true` and `hadHistoricalHumanParticipation=true`; include the referenced human message in normalized facts when its ID and content are available.

If no human is known yet, paginate:

1. Initialize `seenIds` from collected message IDs.
2. Set `oldestId` to the numerically smallest collected ID.
3. Read `limit=20` with `before=<oldestId>`.
4. Discard IDs already in `seenIds` and add new IDs.
5. Require the next oldest ID to be numerically smaller than the previous cursor.
6. Continue until a human is found or the thread start is reached.

An empty raw page or raw page shorter than 20 reaches the start. A repeated/unchanged cursor, a page with no new IDs before reaching the start, a missing ID, or an API failure makes collection incomplete. Stop and set `historyScanComplete=false`.

Never stop at an arbitrary page count and never issue the same cursor twice.

#### 3c. Normalize facts

Deduplicate by ID and sort oldest to newest by numeric Discord ID. Serialize JSON with a structured writer, not hand-escaped shell text.

```json
{
  "name": "thread name",
  "pinned": false,
  "lastMessageAgeMinutes": 123,
  "messageOrder": "oldest_to_newest",
  "historyScanComplete": true,
  "humanInitiated": true,
  "hadHistoricalHumanParticipation": true,
  "messages": [
    {"messageId": "123", "content": "...", "isBot": false},
    {"messageId": "124", "content": "...", "isBot": true}
  ],
  "operationalThreadPrefixes": ["🤖 "]
}
```

Set `historyScanComplete=true` only after finding historical human participation or reaching the thread start. Recent-window absence of human never proves bot-only history.

#### 3d. Classify once

```bash
python3 <skill_dir>/scripts/classify-thread.py < /tmp/thread-facts-<thread_id>.json
```

Call the classifier at most once per thread. Never override a non-`uncertain` result. Treat `facts_invalid` and `facts_incomplete` as keep decisions. Keep a latest unanswered human request or bot question, including operational threads. A new human request invalidates earlier closure; a later answer still follows the normal idle gate. A prefixed thread is operational only when complete facts prove no historical human participation.

### 4. Archive

```bash
bash <skill_dir>/scripts/archive-thread.sh <thread_id>
```

Dry-run:

```bash
bash <skill_dir>/scripts/archive-thread.sh --dry-run <thread_id>
```

Report non-2xx responses as `archive_failed_<status>`.

### 5. Report

Strict icons:
- `✅` archived
- `⏸️` kept
- `⏭️` pinned/skipped
- `🧪` would archive in dry-run

```
🗂️ Thread 归档 · HH:MM
✅ thread名 — 归档：reason_code，一句话原因
⏸️ thread名 — 保留：reason_code，一句话原因
⏭️ thread名 — 跳过(pinned)
归档 X / 保留 Y / 跳过 Z
```

Dry-run title: `🗂️ Thread 归档 dry-run · HH:MM`. If empty:

```
🗂️ Thread 归档 · HH:MM
⏸️ 无 Thread
```

Every listed thread appears exactly once.

### 6. Deliver

```
message(action="send", channel="discord", target="channel:<logChannel>")
```
