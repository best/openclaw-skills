---
name: code-reviewer
description: "Standardized code review checklist for AI-generated code. Supports both local diff and PR review workflows."
metadata:
  version: 0.1.2
---

# Code Reviewer — Quality Gate

Review code against a standardized checklist. Works in two modes: local diff review and PR review.

## Review Checklist

1. **Type Safety** — No `any` types, proper generics, strict null checks
2. **Error Handling** — All async ops have try/catch, meaningful error messages
3. **Resource Cleanup** — Streams closed, listeners removed, timers cleared
4. **API Consistency** — Naming conventions, parameter ordering, return types
5. **Tests** — Coverage for happy path + edge cases + error cases
6. **Build** — `pnpm test` passes, `tsc --noEmit` clean
7. **Security** — No hardcoded secrets, proper input validation
8. **Idempotency** — Operations safe to retry (especially for event handlers, webhooks)

## Mode A: Local Diff Review

For reviewing code before pushing:

1. `git diff main..HEAD --stat` to see changed files
2. Review each changed file against checklist
3. Run `pnpm test` to verify
4. Report findings with severity

## Mode B: PR Review (Cron Patrol)

For review-engineer cron patrol or manual PR review:

1. `gh pr list --repo OWNER/REPO --state open` to find PRs
2. `gh pr checks <number>` — CI must pass before code review
   - CI pending → skip, wait for next patrol
   - CI failed → reject with CI failure details
3. `gh pr diff <number>` — review changed code against checklist
4. Verdict:
   - PASS → `gh pr merge <number> --squash`
   - NEEDS_FIX → `gh pr review <number> --request-changes -b "details"`
   - UNCERTAIN → escalate to dev-mgr (via sessions_send if in multi-agent setup)

## Output Format

```
## Review: #N — Title

### Critical
- file.ts:42 — description

### Warning
- file.ts:15 — description

### Info
- file.ts:8 — suggestion

### Verdict: PASS / NEEDS_FIX / ESCALATE
```

## Severity Guide

- **Critical** = must fix before merge (type errors, missing error handling, security issues)
- **Warning** = should fix, can defer (style inconsistency, missing edge case test)
- **Info** = suggestion (optimization, naming improvement)
- **ESCALATE** = reviewer is unsure about a design decision or trade-off

## Integration Notes

- The review-engineer cron patrol embeds the PR workflow inline — this skill provides the detailed checklist reference
- When reviewing AI-generated code, pay extra attention to: test coverage gaps, over-abstraction, hardcoded paths
- Review cadence: every 3-4 development issues, consider a batch cross-file review for architectural consistency
