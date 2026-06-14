---
name: feed-broadcast
description: "Broadcast newly published AI Feed posts through a controlled wrapper with state and delivery guards."
metadata:
  version: 1.2.0
---

# Feed Broadcast Skill

Check newly published AI Feed posts, decide which are worth pushing, and let the wrapper deliver plain Discord text plus update broadcast state.

## Use When

- Scheduled AI Feed broadcast cron fires.
- A user asks to push newly published feed posts.
- A previous broadcast run needs verification or finalization.

## Core Rule

Do not manually query git history or call `message` directly. Use the controlled scripts.

Allowed:

- `exec` to run prepare/finalize.
- `read` the task JSON produced by prepare.
- `write` exactly the decision JSON path specified by the task.

Forbidden:

- Running article Markdown files through interpreters.
- Calling `message` directly.
- Sending Discord cards, components, presentations, effects, or embeds.
- Updating `state/feed-broadcast.json` manually.

## Commands

### Prepare

```bash
python3 scripts/feed_broadcast_ctl.py prepare
```

Prepare writes a task JSON containing new posts, target channels, and the decision file path.

If prepare returns `status=no_content`, stop successfully and stay silent.

### Decision Handoff

Write JSON to the task `decisionPath`:

```json
{
  "status": "ok",
  "selected": [
    {"path": "src/data/blog/2026-06-14/001-example.md", "reason": "high-signal release"}
  ],
  "skipped": [
    {"path": "src/data/blog/2026-06-14/002-example.md", "reason": "incremental duplicate"}
  ],
  "message": "📡 AI Feed · 17:00\n\n🔥 **标题**（8.5）\n一句话推荐理由。\n<https://feed.astralor.com/posts/2026-06-14/001-example/>\n\n→ 全部文章：<https://feed.astralor.com>"
}
```

Selection rules:

- `featured: true` must be selected.
- `score >= 8.0` must be selected.
- `score 7.0-7.9` is optional based on novelty and usefulness.
- `score < 7.0` is skipped unless uniquely valuable.

Message rules:

- Plain Discord text only.
- Wrap links in `<...>`.
- Keep each item to 1-2 sentences.
- If `selected=[]`, `message` must be empty.

### Finalize

```bash
python3 scripts/feed_broadcast_ctl.py finalize
```

Finalize validates the decision, sends the broadcast/log through `openclaw message send`, and updates the state file only after successful delivery.

## Output Contract

Final reply should be one line based on runner stdout:

`📡 播报 HH:MM — 推送 <pushed> 条 / 跳过 <skipped> 条; sent=<sent>; log=<logSent>`

No new posts is a successful silent outcome.

## References

- `scripts/feed_broadcast_ctl.py`: prepare/finalize wrapper.
- `scripts/extract-new-posts.py`: frontmatter extractor.
