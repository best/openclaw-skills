---
name: project-planner
version: 0.1.0
description: Evaluate and prioritize next tasks for OpenLinkOS project. Activate when: (1) need to decide what to work on next, (2) multiple open issues need prioritization, (3) sprint/milestone planning. NOT for: executing tasks, writing code, or reviewing PRs.
---

# Project Planner — Task Prioritization

Evaluate open issues and recommend the highest-value next task.

## Evaluation Criteria (priority order)

1. **Blocking** — Does this unblock other work?
2. **User-facing** — Does this directly improve user experience?
3. **Complexity** — Prefer small wins over large refactors when value is similar
4. **Dependencies** — Are prerequisites met?
5. **Staleness** — Older issues get slight priority boost

## Workflow

1. `gh issue list --state open --json number,title,labels,createdAt,body` in project dir
2. Score each issue against criteria above
3. Output ranked list with reasoning
4. Recommend top 1-3 issues to work on next

## Output Format

```
## Task Priority Report

### Recommended Next: #N — Title
- **Why**: reasoning
- **Effort**: S/M/L
- **Blocks**: issues it unblocks

### Queue
1. #N — Title (score: X/10)
2. #N — Title (score: X/10)
```

## Principles

- Don't create issues — only evaluate existing ones
- If no open issues, report "queue empty"
- Factor in recent devlog context when available
- Prefer issues with clear acceptance criteria

## Project Context

- Repo: `/data/code/github.com/openlinkos/agent`
- Devlog: `/root/.openclaw/workspace/memory/openlinkos-devlog.md`
- GitHub: `https://github.com/openlinkos/agent`
