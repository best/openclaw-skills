# Thread Archiving Judgment Guide

Read this file before classifying threads.

## Facts Contract

Classifier input must satisfy:

- `messageOrder` equals `oldest_to_newest`.
- Every message has a numeric Discord `messageId`.
- Message IDs are unique and strictly increasing.
- `historyScanComplete=true` means historical human participation was found or the thread start was reached.
- `humanInitiated` includes a bot-authored type-21 starter whose referenced parent is human-authored.
- `hadHistoricalHumanParticipation` is independent of the latest window.

Bad order, duplicate/missing IDs, or malformed messages return `keep/facts_invalid`. An unfinished participation scan returns `keep/facts_incomplete`.

## Lookback

When the latest five messages are bots:

1. Read the latest 20-message no-cursor window once.
2. Inspect the thread starter and referenced parent.
3. If participation is unknown, page with the oldest collected ID as `before`.
4. Deduplicate and continue to a human or the thread start.

Never infer bot-only history from a recent finite window.

## Operational Threads

A thread is operational only when its name has an operational prefix and a complete scan proves no human participation.

| Verdict | Reason | Criteria |
|---|---|---|
| keep | `op_needs_attention` | Failure, blocker, permission/approval issue, or manual action. |
| keep | `op_running` | Latest status is running or waiting for results. |
| archive | `op_done_no_human` | Completion/result with no attention or running signal. |
| archive | `op_stale_status_no_human` | Status-only thread older than two hours. |
| keep | `op_recent_status` | Status-only thread newer than two hours. |

Any historical human participation forces normal-thread rules, even with an operational prefix.

## Normal Threads

### Hard question gate

A latest bot question is `keep/bot_question_unanswered`. An older closure phrase cannot override a newer question.

### Human closure

Closure must be human-authored and later than unresolved question/wait/running/blocker/approval/user-action signals. Negated or question forms such as “还没完成” and “完成了吗？” do not close.

Closure phrases: 好了, 搞定, done, 结束, 结束吧, 谢谢, thanks, 确认, 没问题, OK, 可以了, 完成, 完成了, 已完成, 完成吧, 收尾, 收工, 不再需要讨论, 不需要讨论了, 无需讨论, 不用讨论, 可以归档, 归档吧, 可以关闭, 关闭吧.

### Final-answer idle

Within 24 hours, archive `collab_answered_idle` only when:

- historical human participation is known;
- latest message is a bot answer idle for at least 60 minutes;
- latest answer is not a question;
- facts contain no unresolved wait/result, running, blocker/failure, approval, or user-action signal.

### Classification

| Verdict | Reason | Criteria |
|---|---|---|
| archive | `normal_closed` | Valid human closure after pending signals. |
| archive | `collab_answered_idle` | Known human participation and idle final bot answer. |
| archive | `bot_only_old` | Complete scan proves bot-only and older than 24 hours. |
| archive | `collab_completed_old` | Old collaboration is clearly complete. |
| keep | `bot_question_unanswered` | Latest bot message is a question. |
| keep | `waiting_answer` | Blocker, approval, permission, or manual action remains. |
| keep | `waiting_result` | Work/result remains pending. |
| keep | `collab_recent` | Recent collaboration lacks closure/final-idle completion. |
| keep | `recent_no_closure` | Recent normal thread lacks closure. |
| keep | `multi_topic_open` | Any topic remains unresolved. |
| keep | `facts_invalid` | Facts are duplicated, unordered, or malformed. |
| keep | `facts_incomplete` | Participation scan did not reach a trusted stop. |
| keep | `uncertain` | Completion cannot be determined safely. |

When in doubt, keep.

## Regression Scenarios

Must archive:

- Human starter outside the latest 20 messages, 20+ bot/tool updates, final non-question answer, idle 60+ minutes, no pending signal → `collab_answered_idle`.
- Referenced human starter on a bot-authored type-21 message under the same conditions → `collab_answered_idle`.
- Completed bot-only operational thread with a complete history scan → `op_done_no_human`.

Must keep:

- Historical closure followed by a newer bot question.
- Waiting for login, approval, user action, result, or running work.
- Duplicate/unordered message IDs → `facts_invalid`.
- Pagination stopped before human participation or thread start → `facts_incomplete`.

Do not invent thresholds, activity metrics, or cross-thread relationships. Judge each thread independently.
