# Thread Archiving Judgment Guide

Detailed criteria for evaluating whether a Discord thread should be archived, kept, or skipped.

## Bot-only Lookback (Rule 3a)

If the last 5 messages are **all from bots**, expand to 20 messages:

- Human messages found in expanded window → **human-bot collaboration thread**. The human initiated and may still be engaged. Verdict: **keep** (unless explicit closure signal).
- Still no human messages after 20 → truly bot-only thread. Proceed to classification.

## Recency Protection (Rule 3b)

Compare last message timestamp against current time:

- **Within 24h** → only archive with **explicit closure signal** (thanks, confirmation, "done", "结束", "搞定了"). Do NOT archive based on inactivity or "all bot messages" alone.
- **Older than 24h** → classify normally.

This is the ONLY time-based rule. Do not invent additional thresholds.

## Classification Table

| Verdict | Criteria |
|---------|----------|
| **archive** | Clear resolution: thanks/confirmation, question answered, explicit "done"/"结束", or notification consumed |
| **archive** | All bot messages after lookback (3a), no human participation, AND older than 24h (3b) |
| **keep** | Open question unanswered, action items pending, waiting for response, active discussion |
| **keep** | Last message implies next step: "wait for results", "看看效果", "等结果", "触发一下" |
| **keep** | Bot sent proposal/question but human hasn't replied — busy ≠ disengaged |
| **keep** | Human-bot collaboration thread identified by lookback (3a) |
| **keep** | Within 24h recency protection (3b), no closure signal |
| **keep** | Can't determine from messages read |

**When in doubt, keep.** Archiving a live conversation is worse than keeping a finished one.

**Critical:** "task completed" = entire discussion resolved with human confirmation, not a single sub-step done. User not responding ≠ conversation over.

## Anti-hallucination Guard

Use ONLY the criteria above plus rules 3a/3b. Do NOT invent:
- Additional time thresholds ("48h inactive", "1 week old")
- Activity metrics
- Cross-thread relationships ("absorbed by another thread")
- Any rules not in this document

Each thread is judged independently. Uncovered case → **keep**.

## Examples

### Correct: archive

> **"CI 构建失败排查"** — User: "好了，问题解决了，谢谢" → archive (explicit confirmation)

> **"版本发布通知"** — All bot messages, no human replied → archive (bot-only, no participation)

### Correct: keep

> **"服务器搭建讨论"** — Bot asked "方案 A 还是方案 B？" → keep (waiting for user)

> **"密钥配置"** — Bot said "你把这个加到目标机器上" → keep (action pending on user)

> **"API 供应商评估"** — Last 5 all bot exec logs, lookback found human, within 24h → keep (collaboration + recency)

### Common mistakes

> ❌ archive "基础设施讨论" — "absorbed by another thread" → Wrong: cross-thread reasoning forbidden

> ❌ archive "部署方案讨论" — "bot completed the task" → Wrong: sub-task ≠ entire discussion resolved

> ❌ archive "供应商续费讨论" — "all 5 bot messages" → Wrong: didn't do lookback; human was involved earlier
