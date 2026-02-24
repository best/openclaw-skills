---
name: cc-iterator
version: 0.1.3
description: "Autonomous CC (Claude Code) iteration loop. Manages background coding agent tasks with pull-based issue tracking."
---

# CC Iterator — Autonomous Development Loop

Drive OpenLinkOS project forward by managing CC (Claude Code) background tasks.

## Core Loop (Pull-based)

1. **Check** — `process action:list` for active CC sessions
2. **Harvest** — If CC completed: verify with `pnpm test`, `git push`, close issue
3. **Next** — `gh issue list --state open` → has open issue → start CC
4. **Wait** — No open issues → HEARTBEAT_OK (never auto-create issues)

Issues come from discussions, user feedback, or bug reports. Patrol executes, it does not decide.

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
- Exit code 143 (SIGTERM) = killed, check if timed out
- No output after 25+ min = likely hung → kill and retry
- Check `git status` to confirm no code changes before retrying
- If CC partially completed: check `git log`, continue from breakpoint

### Wake Event Failure

The `openclaw system event` at the end of CC prompts may silently fail if:
- Gateway restarted during CC execution (event has no delivery target)
- LLM provider outage caused the parent session to expire

When CC completes but no wake event arrives, the cron patrol loop detects completion
via `process action:list` (exit code 0). Don't rely solely on wake events.

### Debugging CC Failures (post-2026.2.22)

OpenClaw 2026.2.22+ hides tool error details by default. When investigating CC failures:
- Use `/verbose on` in the session to see full error payloads
- Background tasks are no longer killed by default timeout (previous failure mode removed)
- Execution and delivery status are now tracked separately — a CC may finish (execution OK)
  but its wake event may fail to deliver (delivery failed)

## Lessons Learned

- CC self-check won't catch CI environment differences (local has dist cache, CI doesn't)
- Self-check prompt should include: verify CI workflow step ordering
- Simple fixes (e.g. reordering CI steps) can be done manually, no need to spawn CC

## Review Cadence

- Every 3-4 development issues, create a batch review issue
- Review checks: type safety, error handling, resource cleanup, API consistency

## Project Context

- Repo: `/data/code/github.com/openlinkos/agent`
- Devlog: `memory/openlinkos-devlog.md`
- GitHub: `https://github.com/openlinkos/agent`
