# Thread Archiving Judgment Guide

Detailed criteria for evaluating whether a Discord thread should be archived, kept, or skipped.

**This file is mandatory reading. Do not classify any thread without loading these rules first.**

## Bot-only Lookback (Rule 3a)

If the last 5 messages are **all from bots**, expand to 20 messages:

- Human messages found in expanded window → **human-bot collaboration thread**. Apply normal-thread rules below. Within 24h, keep unless explicit human closure. Older than 24h, classify by unresolved questions/action items/completion state.
- Still no human messages after 20 → truly bot-only thread. Proceed to classification.

## Operational Thread Policy

Operational threads are bot-created task/status threads. The default signal is a title prefix `🤖 ` plus **no human messages** in the expanded message window.

These threads are not normal conversations and do not require human closure confirmation. Evaluate them before normal recency gates:

| Verdict | Reason code | Criteria |
|---------|-------------|----------|
| **keep** | `op_needs_attention` | Any message indicates failure, blocked state, permission issue, approval required, waiting for user/operator, or manual action needed. Keywords include: `error`, `failed`, `blocked`, `approval`, `permission`, `403`, `异常`, `失败`, `阻塞`, `等待确认`, `需要用户`, `需要人工`, `权限不足` |
| **keep** | `op_running` | Last messages indicate the task is still running or waiting for results: `running`, `in progress`, `started`, `working`, `执行中`, `进行中`, `等待结果`, `还在跑` |
| **archive** | `op_done_no_human` | No human messages, no attention/running signal, and messages indicate completion/result delivery: `finished`, `completed`, `done`, `ok`, `任务完成`, `已完成`, `结果`, `summary` |
| **archive** | `op_stale_status_no_human` | No human messages, no attention/running signal, and last message is an old status-only notification. Use only when older than 2h. |
| **keep** | `op_recent_status` | No human messages, no attention/running signal, but last status-only message is newer than 2h. |

If an operational-prefix thread contains any human message, stop using this policy and evaluate as a normal human-bot collaboration thread.

## Recency Protection (Rule 3b)

Compare last message timestamp against current time:

- **Within 24h** → for normal threads, only archive with **explicit human closure signal** (thanks, confirmation, "done", "结束", "搞定了", "完成吧", "不再需要讨论了", "可以归档"). Do NOT archive based on inactivity alone.
- **Older than 24h** → classify normally.

For normal threads, this is the only time-based rule. Operational threads have their own 2h status-only threshold above.

## Classification Table

| Verdict | Reason code | Criteria |
|---------|-------------|----------|
| **archive** | `normal_closed` | Clear resolution: human thanks/confirmation, question answered, explicit "done"/"结束", or notification consumed |
| **archive** | `bot_only_old` | All bot messages after lookback (3a), no human participation, AND older than 24h (3b) |
| **archive** | `collab_completed_old` | Human-bot collaboration older than 24h, with no unanswered bot question, no pending user/operator action, no failure/blocker, and a clear completed or consumed notification state |
| **keep** | `waiting_answer` | Open question unanswered, action items pending, waiting for response, active discussion |
| **keep** | `waiting_result` | Last message implies next step: "wait for results", "看看效果", "等结果", "触发一下" |
| **keep** | `bot_question_unanswered` | Bot sent proposal/question but human hasn't replied — busy ≠ disengaged |
| **keep** | `collab_recent` | Human-bot collaboration identified by lookback (3a) AND last message is within 24h without human closure. If a human explicitly says the thread is complete or no longer needs discussion, archive as `normal_closed` instead. |
| **keep** | `recent_no_closure` | Within 24h recency protection (3b), no closure signal |
| **keep** | `multi_topic_open` | Thread has multiple topics and any topic is unresolved |
| **keep** | `uncertain` | Can't determine from messages read |

**When in doubt, keep.** Archiving a live conversation is worse than keeping a finished one.

**Critical:** "task completed" = entire discussion resolved with human confirmation, not a single sub-step done. User not responding ≠ conversation over.

## Anti-hallucination Guard

Use ONLY the criteria above plus rules 3a/3b. Do NOT invent:
- Additional time thresholds ("48h inactive", "1 week old") for normal threads
- Activity metrics
- Cross-thread relationships ("absorbed by another thread")
- Any rules not in this document

Each thread is judged independently. Uncovered case → **keep** with `uncertain`.

## Examples

### Correct: archive

> **"CI 构建失败排查"** — User: "好了，问题解决了，谢谢" → archive (`normal_closed`)

> **"PPT 生成优化调研"** — User: "完成吧，不再需要讨论了" → archive (`normal_closed`)

> **"版本发布通知"** — All bot messages, no human replied, older than 24h → archive (`bot_only_old`)

> **"🤖 ppt-skills-research"** — Bot-only subagent thread, task completed, no failure/approval/user-waiting signal → archive (`op_done_no_human`)

> **"旧日报整理"** — Human asked, bot produced final answer, no unanswered question/action item, older than 24h → archive (`collab_completed_old`)

### Correct: keep

> **"服务器搭建讨论"** — Bot asked "方案 A 还是方案 B？" → keep (`bot_question_unanswered`)

> **"密钥配置"** — Bot said "你把这个加到目标机器上" → keep (`waiting_answer`)

> **"API 供应商评估"** — Last 5 all bot exec logs, lookback found human, within 24h → keep (`collab_recent`)

> **"余额检查脚本修复"** — Bug fixed and confirmed, but bot then proposed a new solution and asked "要做吗？" with no reply → keep (`bot_question_unanswered`)

> **"🤖 migration-check"** — Bot-only thread but last message says "failed / needs approval" → keep (`op_needs_attention`)

> **"🤖 long-research"** — Bot-only thread but last message says "still running / waiting for results" → keep (`op_running`)

### Common mistakes

> ❌ archive "基础设施讨论" — "absorbed by another thread" → Wrong: cross-thread reasoning forbidden

> ❌ archive "部署方案讨论" — "bot completed the task" → Wrong: sub-task ≠ entire discussion resolved

> ❌ archive "供应商续费讨论" — "all 5 bot messages" → Wrong: didn't do lookback; human was involved earlier

> ❌ keep every historical human-bot thread forever → Wrong: after 24h, completed collaborations can archive if no open question/action/blocker remains

> ❌ archive "Cron检查问题" with reason "方案已确定" — Bot proposed a solution and asked for confirmation, human never replied → Wrong: proposal ≠ decision; unanswered question = keep
