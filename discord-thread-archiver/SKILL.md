---
name: discord-thread-archiver
version: 0.8.0
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
| **archive** | Clear resolution: thanks/confirmation, question answered, explicit "done"/"结束", or notification consumed with no follow-up needed |
| **archive** | All messages from bots, no human participation |
| **keep** | Open question unanswered, action items pending, waiting for response, active discussion |
| **keep** | Last message implies a next step: "wait for results", "let's see", "看看效果", "等结果", "触发一下" — a completed sub-task does NOT mean the discussion is over |
| **keep** | Bot/assistant sent a proposal, analysis, or question but the human hasn't replied yet — they may be busy, not disengaged |
| **keep** | Can't determine from 5 messages |

**When in doubt, keep the thread.** Archiving a live conversation is worse than keeping a finished one.

**Critical rule:** "task completed" means the *entire discussion's purpose* is resolved with explicit human confirmation, not that a single action or sub-step was performed. A user not responding ≠ conversation over — humans have other things to do.

**Anti-hallucination guard:** Use ONLY the criteria listed in the table above. Do NOT invent time thresholds (e.g. "24h inactive"), activity metrics, cross-thread relationships (e.g. "absorbed by another thread"), or any rules not explicitly written in this document. Each thread is judged independently. If the table doesn't cover a case, the verdict is **keep**.

For each thread, produce a verdict with a one-sentence reason summarizing what was observed in the messages.

### Examples

**✅ Correct: archive**

> Thread: "CI 构建失败排查"
> Last messages: Bot found the issue → User: "好了，问题解决了，谢谢"
> Verdict: archive — user explicitly confirmed resolution

> Thread: "版本发布通知"
> Last messages: Bot posted changelog, no human replied, all messages are from bot
> Verdict: archive — all messages from bots, no human participation

**✅ Correct: keep**

> Thread: "服务器搭建讨论"
> Last messages: Bot proposed a plan and asked "你觉得用方案 A 还是方案 B？"
> Verdict: keep — bot asked a question, waiting for user response

> Thread: "密钥配置"
> Last messages: Bot gave user an SSH public key and said "你把这个加到目标机器上就行，然后告诉我端口"
> Verdict: keep — action item pending on user side, waiting for response

> Thread: "架构规划"
> Last messages: Bot outlined a directory structure and asked "仓库名字叫 X 可以吗？还是你想叫别的？"
> Verdict: keep — bot asked a decision question, user hasn't replied yet

**❌ Wrong: common mistakes**

> Thread: "基础设施讨论"
> Wrong verdict: archive — "topic absorbed by another related thread, no reply for 1.5 hours"
> Why wrong: (1) cross-thread reasoning is forbidden (2) time threshold is invented (3) bot's last message asked a question → should be keep

> Thread: "部署方案讨论"
> Wrong verdict: archive — "bot completed the deployment task"
> Why wrong: a sub-task completing ≠ entire discussion resolved; user hasn't confirmed the discussion is done

## Token Optimization

1. **ONE thread-list call per guild** — never per-channel
2. **limit=5** for message reads — sufficient for judgment
3. Only pinned threads skip message reading; all others are evaluated
