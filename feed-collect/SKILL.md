---
name: feed-collect
description: "AI Feed deterministic collection runner. Use to collect Miniflux/HN/GitHub candidates into data/candidates.json for feed-score."
metadata:
  version: 2.3.0
---

# Feed Collect Skill

Deterministically collect AI Feed candidates and write them to the feed repository for `feed-score`.

## Use When

- Scheduled AI Feed collection cron fires.
- A user asks to manually collect new AI Feed candidates.
- You need to verify collection state after a failed run.

## Core Rule

Do not reimplement collection logic in the agent. Run the controlled entrypoint and report its stdout.

```bash
scripts/run-collect.sh
```

Allowed runtime behavior:

- Use `exec` to run the scripts below.
- Read script stdout/stderr for diagnosis.
- Do not use `edit`, `apply_patch`, or ad hoc heredoc Python during collection.
- Do not call `message` directly from this skill; delivery belongs to cron delivery or a wrapper.
- Do not run `git add -A`, `git add .`, or commit files outside `data/candidates.json` and `data/seen.json`.

## Commands

### Collect

```bash
scripts/run-collect.sh
```

Equivalent explicit form:

```bash
python3 scripts/feedctl.py collect --commit --push
```

### Verify Local State

```bash
python3 scripts/feedctl.py verify
```

## Configuration

The runner reads configuration from environment variables:

- `FEED_REPO`: feed repository path. Must be set by the local cron or shell environment.
- `MINIFLUX_CONFIG`: local JSON config path, or set `MINIFLUX_BASE_URL`, `MINIFLUX_USERNAME`, and `MINIFLUX_PASSWORD`.
- `MINIFLUX_LIMIT`: page size for unread entries. Defaults to `200`.
- `HN_LIMIT`: Hacker News supplemental limit. Defaults to `20`.
- `GITHUB_TRENDING_LIMIT`: GitHub supplemental limit. Defaults to `20`.

Secrets must stay in local config or environment. Do not print credential values or credential file paths.

## Output Contract

The runner prints one JSON object to stdout:

```json
{
  "status": "ok | no_content | failed",
  "new_candidates": 0,
  "miniflux_entries": 0,
  "hn_items": 0,
  "github_items": 0,
  "marked_read": 0,
  "committed": false,
  "commit": "",
  "pushed": false,
  "message": "human-readable summary",
  "final": "📡 采集完成 HH:MM — no new candidates; 新增 0 条; commit=none; pushed=false"
}
```

`ok` and `no_content` are successful cron outcomes. `failed` exits non-zero. If `final` is present, copy it exactly for the cron reply.

## Failure Semantics

- Dirty non-generated files in the feed repository: fail fast and report the paths.
- Miniflux fetch failure: fail; do not mark unread entries as read.
- HN/GitHub supplemental fetch failure: continue and include a warning.
- Invalid `data/seen.json` or `data/candidates.json`: fail before writing.
- No new candidates: do not commit; return `status=no_content`.

## References

- `references/collect-spec.md`: collection schema, source mapping, dedupe rules.
- `scripts/feedctl.py`: deterministic runner.
- `scripts/run-collect.sh`: cron-friendly wrapper.
- `scripts/prepare-feed-repo.sh`: generated-artifact cleanup and safe pull helper.
