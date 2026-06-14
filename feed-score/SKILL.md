---
name: feed-score
description: "Score and publish AI Feed candidates through a controlled runner. Agent only writes scored-results JSON."
metadata:
  version: 2.2.0
---

# Feed Score Skill

Score AI Feed candidates and publish generated posts. This skill is a controlled human-in-the-loop runner: scripts own repository state, validation, generation, build, git commit, and push; the agent only performs scoring judgment and writes `scored-results.json`.

## Use When

- Scheduled AI Feed score/publish cron fires.
- A user asks to score collected candidates.
- You need to finalize or clean up a half-finished score run.

## Core Rule

Do not execute the old Markdown procedure step-by-step. Use `feed_score_ctl.py`.

Allowed:

- `exec` for the commands below.
- `read` the generated task JSON and `references/scoring-rules.md`.
- `write` exactly the scored-results JSON path specified by the task.

Forbidden:

- `git add -A`, `git add .`, or committing arbitrary files.
- Editing repository files directly other than the scored-results JSON handoff.
- Using `message` directly; cron delivery handles logs.
- Comparing current candidates against `data/seen.json` for duplicate decisions.

## Commands

### Prepare Task

```bash
python3 scripts/feed_score_ctl.py prepare
```

Prepare outputs a JSON task path. Read that task before scoring.

If prepare returns `status=no_content`, stop successfully.

### Score Handoff

Write a top-level JSON object to the task `scoredResultsPath`:

```json
{
  "evaluated": 3,
  "scoredAt": "2026-06-14T17:00:00+08:00",
  "results": []
}
```

Rules:

- Every task candidate must appear exactly once in `results`.
- `verdict` is only `publish` or `skip`.
- `score >= 6.5` should usually publish.
- `publish` entries must include all fields required by `references/scoring-rules.md`.
- `skip` entries must include `reason`; duplicate skips must include `duplicateOf`.

### Finalize

```bash
python3 scripts/feed_score_ctl.py finalize --push
```

Finalize validates scored results, generates posts, runs build, commits/pushes generated posts, clears processed candidates, and prints JSON summary.

## Output Contract

Final reply should be one line based on runner stdout:

`📋 评分完成 HH:MM — <message>; generated=<generated>; cleanup=<cleanupCommitted>; pushed=<publishPushed|cleanupPushed>`

`status=ok` and `status=no_content` are successful cron outcomes. `status=failed` or shell non-zero is failure.

## References

- `references/scoring-rules.md`: scoring dimensions, thresholds, output schema.
- `scripts/feed_score_ctl.py`: prepare/finalize state machine.
- `scripts/generate-posts.py`: deterministic Markdown generator.
- `scripts/validate-score-results.py`: schema and coverage validator.
