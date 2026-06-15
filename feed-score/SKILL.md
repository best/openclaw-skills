---
name: feed-score
description: "Score and publish AI Feed candidates through a controlled runner. Agent only writes scored-results JSON."
metadata:
  version: 2.4.0
---

# Feed Score Skill

Score AI Feed candidates and publish generated posts. This skill is a controlled human-in-the-loop runner: scripts own repository state, validation, generation, optional build, git commit, and push; the agent only performs scoring judgment and writes `scored-results.json`.

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

Prepare limits each task to a small batch by default (`FEED_SCORE_LIMIT=30`). Score only the task `candidates` array. Remaining candidates stay in `data/candidates.json` for later runs.

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

- Every task candidate must appear exactly once in `results`; do not include URLs outside the task batch.
- `verdict` is only `publish` or `skip`.
- `score >= 7.0` should usually publish; lower scores must not publish.
- `publish` entries must include all fields required by `references/scoring-rules.md`.
- `skip` entries must include `reason`; duplicate skips must include `duplicateOf`.

### Finalize

```bash
python3 scripts/feed_score_ctl.py finalize --push
```

Finalize validates scored results, generates posts, commits/pushes generated posts, clears processed candidates, and prints JSON summary.

By default finalize skips the full Astro build so cron stays short and does not leave generated artifacts dirty. Use `FEED_SCORE_RUN_BUILD=1` only for manual strict verification; `FEED_SCORE_BUILD_TIMEOUT` caps that optional build.

## Output Contract

Final reply should copy `final` from runner stdout when present. Otherwise use:

`📋 评分完成 HH:MM — <message>; generated=<generated>; cleanup=<cleanupCommitted>; pushed=<publishPushed|cleanupPushed>`

`status=ok` and `status=no_content` are successful cron outcomes. `status=failed` or shell non-zero is failure.

## References

- `references/scoring-rules.md`: scoring dimensions, thresholds, output schema.
- `scripts/feed_score_ctl.py`: prepare/finalize state machine.
- `scripts/generate-posts.py`: deterministic Markdown generator.
- `scripts/validate-score-results.py`: schema and coverage validator.
