---
name: cc-iterator
version: 0.1.0
description: Autonomous CC (Claude Code) iteration loop for OpenLinkOS project. Activate when: (1) heartbeat/cron triggers project patrol, (2) CC task completes and next step needed, (3) need to start/monitor/review CC development tasks. NOT for: simple file edits, reading code, non-project work.
---

# CC Iterator — Autonomous Development Loop

Drive OpenLinkOS project forward by managing CC (Claude Code) background tasks.

## Core Loop (拉式驱动)

1. **Check** — `process action:list` for active CC sessions
2. **Harvest** — If CC completed: verify with `pnpm test`, `git push`, close issue
3. **Next** — `gh issue list --state open` → has open issue → start CC
4. **Wait** — No open issues → HEARTBEAT_OK（不自主创建 issue）

Issue 来源：讨论产生的需求、用户反馈、bug 发现。巡逻只负责执行，不负责决策。

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

## Lessons Learned

- CC 自检不会发现 CI 环境差异（本地有 dist 缓存，CI 没有）
- 自检 prompt 应包含：检查 CI workflow 步骤顺序
- 简单修复（如调换 CI 步骤顺序）直接手动改，不需要启动 CC

## Review Cadence

- Every 3-4 development issues, create a batch review issue
- Review checks: type safety, error handling, resource cleanup, API consistency

## Project Context

- Repo: `/data/code/github.com/openlinkos/agent`
- Devlog: `memory/openlinkos-devlog.md`
- GitHub: `https://github.com/openlinkos/agent`
