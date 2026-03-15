---
name: discord-thread-archiver
version: 0.6.0
description: "Smart Discord thread archiving. Use when: (1) running periodic thread cleanup, (2) evaluating whether Discord threads should be archived. Agent reads thread messages, judges conversation status, and returns structured verdicts."
---

# Discord Thread Archiver

Evaluate active Discord threads and judge whether conversations have concluded. This skill handles **judgment only** — the caller decides how to act on results (archive, report, notify).

## Procedure

### 1. List threads (ONE call per guild)

Call `thread-list` exactly **once** with `guildId`. This returns ALL active threads across every channel in the guild. Do NOT loop over channels — that produces duplicate data and wastes tokens.

```
message(action="thread-list", channel="discord", guildId="<guild>")
```

If the result is empty (no active threads), return immediately with an empty verdict list.

### 2. Skip pinned threads

Only skip threads with `last_pin_timestamp` present — these are explicitly marked for retention. Mark them as `skipped (pinned)`.

All other threads proceed to AI judgment.

### 3. AI judgment — read messages and decide

For every non-pinned thread, read the last 5 messages:

```
message(action="read", channel="discord", target="channel:<thread_id>", limit=5)
```

Classify the conversation:

| Verdict | Criteria |
|---------|----------|
| **archive** | Clear resolution: thanks/confirmation, question answered, task completed, explicit "done"/"结束", or notification consumed with no follow-up needed |
| **archive** | All messages from bots, no human participation |
| **keep** | Open question unanswered, action items pending, waiting for response, active discussion |
| **keep** | Can't determine from 5 messages |

**When in doubt, keep the thread.** A user not responding ≠ conversation over.

For each thread, produce a verdict with a one-sentence reason summarizing what was observed in the messages.

## Token Optimization

1. **ONE thread-list call per guild** — never per-channel
2. **limit=5** for message reads — sufficient for judgment
3. Only pinned threads skip message reading; all others are evaluated
