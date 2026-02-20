---
name: cc-iterator
version: 0.1.0
description: Autonomous CC (Claude Code) iteration loop for OpenLinkOS project. Activate when: (1) heartbeat/cron triggers project patrol, (2) CC task completes and next step needed, (3) need to start/monitor/review CC development tasks. NOT for: simple file edits, reading code, non-project work.
---

# CC Iterator — Autonomous Development Loop

Drive OpenLinkOS project forward by managing CC (Claude Code) background tasks.

## Core Loop

1. **Check** — `process action:list` for active CC sessions
2. **Harvest** — If CC completed: `process action:log sessionId:xxx`, verify with `pnpm test`
3. **Push** — `git push origin master` in project dir
4. **Next** — `gh issue list --state open` → pick highest priority → start CC
5. **Create** — If no open issues: create next issue based on project roadmap, then start CC

## Starting CC

```bash
exec pty:true background:true workdir:/data/code/github.com/openlinkos/agent command:"IS_SANDBOX=1 claude --dangerously-skip-permissions -p 'PROMPT' --output-format text"
```

- No timeout
- Prompt ends with: `When done: gh issue close N && openclaw system event --text "Done: SUMMARY" --mode now`
- Return immediately after starting, never poll-wait

## CC Prompt Template

```
1. Task context: implementing X, Issue #N
2. Current state: N tests passing
3. Specific files and responsibilities
4. Requirements: tests, typecheck, build, no any types
5. Closing: git commit + gh issue close + openclaw system event
```

## Failure Detection

- Runtime < 2 min + minimal output = CC didn't start (API issue) → retry
- Check `git status` to confirm no code changes before retrying
- If CC partially completed: check `git log`, continue from breakpoint

## Review Cadence

- Every 3-4 development issues, create a batch review issue
- Review checks: type safety, error handling, resource cleanup, API consistency

## Project Context

- Repo: `/data/code/github.com/openlinkos/agent`
- Devlog: `memory/openlinkos-devlog.md`
- GitHub: `https://github.com/openlinkos/agent`
