---
name: evolution-engine
version: 0.1.0
description: "PCEC (Plan-Check-Evolve-Commit) self-evolution engine for continuous workflow improvement."
---

# Evolution Engine — PCEC Self-Evolution

Drive continuous improvement of workflows, capabilities, and best practices.

## PCEC Cycle

1. **Plan** — Read capability tree, identify what to review
2. **Check** — Audit current state (code health, dependencies, process efficiency)
3. **Evolve** — Make one concrete improvement
4. **Commit** — Update capability tree / MEMORY.md / workflow files

## Active Period

- Review recent CC iterations for patterns
- Abstract repeated patterns into templates
- Update capability tree with new learnings
- Frequency: every 3 hours

## Idle Period

- Lightweight checks only:
  - `pnpm test` — code health
  - `pnpm outdated` — dependency audit
  - `git status` — repo cleanliness
  - Memory file review and consolidation
- Skip if no activity since last PCEC
- Frequency: 6 hours or skip

## Anti-Evolution Lock

- Don't evolve for evolution's sake
- Don't create issues
- Don't repeat audits within 24h
- Simple > clever
- Stability > novelty

## Key Files

- Capability tree: `/root/.openclaw/workspace/memory/cc-capability-tree.md`
- Long-term memory: `/root/.openclaw/workspace/MEMORY.md`
- Daily notes: `/root/.openclaw/workspace/memory/`
- Project: `/data/code/github.com/openlinkos/agent`
