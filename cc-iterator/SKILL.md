---
name: cc-iterator
version: 0.1.4
description: "Autonomous CC (Claude Code) iteration loop. Manages background coding agent tasks with pull-based issue tracking."
---

# CC Iterator — Autonomous Development Loop

Drive OpenLinkOS project forward by managing CC (Claude Code) background tasks.

## Core Loop (Pull-based)

1. **Check** — `process action:list` for active CC sessions
2. **Harvest** — If CC completed: verify with `pnpm test`, `git push`, check CI, close issue
3. **Self-check** — Spawn a review CC to audit the just-completed work (see below)
4. **Next** — `gh issue list --state open` → has open issue → start CC
5. **Wait** — No open issues → HEARTBEAT_OK (never auto-create issues)

Issues come from discussions, user feedback, or bug reports. Patrol executes, it does not decide.

## Starting CC

```bash
exec pty:true background:true workdir:/data/code/github.com/openlinkos/agent command:"IS_SANDBOX=1 claude --dangerously-skip-permissions -p 'PROMPT' --output-format text"
```

- No timeout
- Prompt ends with: `When done: gh issue close N && openclaw system event --text "Done: SUMMARY" --mode now`
- Return immediately after starting, never poll-wait

## CC Prompt Templates

### Development Task

```
1. Role and context: implementing X package for OpenLinkOS, Issue #N
2. Current state: N tests passing, packages A/B/C already completed
3. Specific files: list every file and its responsibility
4. Quality requirements: tests, typecheck, build, no any types
5. Closing: git commit + gh issue close N + openclaw system event
```

**Tips from real usage:**
- CC can handle multiple packages in one session (e.g., CLI + Channels + Memory together)
- More detailed file structure in the prompt → higher quality output
- CC self-commits; no need to manually run git operations after

### Self-Check (Code Review)

After each development CC completes, spawn a **separate** CC session for review:

```
1. Scope: review packages/files changed in the last N commits
2. Checklist: type safety, error handling, async patterns, resource leaks, edge cases
3. CI alignment: verify CI workflow step ordering matches local assumptions
4. Action: fix problems directly and commit
5. Closing: openclaw system event --text "Review done: SUMMARY" --mode now
```

**Why self-check matters:**
- Averages 2-4 bugs found per review — always worth doing
- Self-check won't catch CI environment differences (local has dist cache, CI doesn't)
- Include "verify CI workflow step ordering" in review prompt to catch this gap

## CI Verification

After `git push`, always verify CI:

```bash
gh run list --limit 3          # check latest runs
gh run view <run-id>           # inspect a specific run
gh run view <run-id> --log     # full logs on failure
```

- **CI passes** → proceed to close issue
- **CI fails, small fix** (e.g., reordering steps) → fix manually, no need to spawn CC
- **CI fails, complex** → analyze logs, spawn CC with fix prompt

## Failure Detection

- Runtime < 2 min + minimal output = CC didn't start (API issue) → retry
- Exit code 143 (SIGTERM) = killed, check if timed out
- No output after 25+ min = likely hung → kill and retry
- Check `git status` to confirm no code changes before retrying

### Breakpoint Resume

If CC partially completed (crashed, hung, or killed mid-work):

1. `git log --oneline -5` — see what CC already committed
2. `git status` — check for uncommitted work
3. Construct a continuation prompt from the breakpoint: describe what's done, what remains
4. Start a new CC with the continuation prompt

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

## Review Cadence

- Self-check after every development CC (see Self-Check template above)
- Every 3-4 development issues, create a batch review issue for cross-cutting concerns
- Batch review checks: API consistency across packages, shared pattern adherence

## Project Context

- Repo: `/data/code/github.com/openlinkos/agent`
- Devlog: `memory/openlinkos-devlog.md`
- GitHub: `https://github.com/openlinkos/agent`
