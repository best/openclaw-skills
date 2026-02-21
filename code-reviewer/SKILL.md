---
name: code-reviewer
version: 0.1.0
description: Standardized code review for CC-generated code. Activate when: (1) CC completes a development task, (2) batch review after 3-4 issues, (3) pre-push quality gate. NOT for: writing code, fixing bugs directly, or project planning.
---

# Code Reviewer — Quality Gate

Review CC-generated code against a standardized checklist.

## Review Checklist

1. **Type Safety** — No `any` types, proper generics
2. **Error Handling** — All async ops have try/catch, meaningful error messages
3. **Resource Cleanup** — Streams closed, listeners removed, timers cleared
4. **API Consistency** — Naming conventions, parameter ordering, return types
5. **Tests** — Coverage for happy path + edge cases + error cases
6. **Build** — `pnpm test` passes, `tsc --noEmit` clean

## Workflow

1. `git diff main..HEAD --stat` to see changed files
2. Review each changed file against checklist
3. Run `pnpm test` to verify
4. Report findings with severity (critical/warning/info)

## Output Format

```
## Review: #N — Title

### Critical
- file.ts:42 — description

### Warning
- file.ts:15 — description

### Info
- file.ts:8 — suggestion

### Verdict: PASS / NEEDS_FIX
```

## Principles

- Critical = must fix before merge
- Warning = should fix, can defer
- Info = style/optimization suggestion
- If NEEDS_FIX: create a fix issue or let CC handle directly
- Every 3-4 issues, do a batch cross-file review

## Project Context

- Repo: `/data/code/github.com/openlinkos/agent`
- Tech: TypeScript, pnpm monorepo, vitest
