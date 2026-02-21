---
name: evolution-engine
version: 0.2.0
description: "PCEC (Plan-Check-Evolve-Commit) self-evolution engine. Drives capability-driven evolution of agent skills."
---

# Evolution Engine — PCEC Self-Evolution

Periodic Cognitive Expansion Cycle. Every 3 hours, identify and commit at least one real improvement.

## Core Principle: Capability-Driven Evolution

The goal is not to complete tasks, but to make future tasks easier. When you notice:
- A step you invented to solve a problem that could be reused
- A tool call sequence you've combined multiple times
- A pattern the user keeps requesting

That's an evolution trigger. Abstract it → internalize it → ship it as a skill.

## PCEC Cycle

1. **Plan** — Read capability tree + recent memory files, identify what to review
2. **Check** — Audit: what worked, what failed, what was repeated
3. **Evolve** — Make one concrete improvement (new skill, updated skill, new strategy)
4. **Commit** — Update files, git commit, git push to skills repo

## Evolution Targets (pick at least one per cycle)

### A. New Capability
- Something you did ad-hoc that should become a skill
- A multi-step workflow that can be abstracted into reusable steps

### B. New Abstraction
- Elevate a specific solution into a general problem class
- Merge two similar capabilities into one stronger one

### C. New Leverage
- A structural change that reduces steps, tool calls, or failure rate
- Optimize an existing skill based on real usage patterns

## Capability Abstraction Template

When abstracting a new capability, define:
- **Input**: what triggers it
- **Output**: what it produces
- **Invariants**: what never changes
- **Parameters**: what varies per invocation
- **Failure modes**: how it can break

## Skill Shipping

When evolution produces a new or updated skill:
1. Write/update SKILL.md in `/data/code/github.com/best/openclaw-skills/`
2. Symlink to `~/.openclaw/workspace/skills/` if new
3. `git commit && git push`
4. Update capability tree

## Anti-Evolution Lock

Priority order (never violate):
1. Stability
2. Explainability
3. Reusability
4. Extensibility
5. Novelty (always last)

Forbidden:
- Adding complexity just to seem smarter
- Vague concepts replacing executable strategies
- "Feels right" as a decision basis
- Summary-only cycles (must produce real change)
- Creating issues autonomously

If a capability can't be clearly described (input/output/failure), it must not exist.

## Stagnation Breaker

If 2 consecutive cycles (6h) produce no real improvement, force one of:
- Challenge a default assumption
- Rethink from a 10x weaker agent's perspective
- Ask: "if this runs 1000 times, what breaks?"

## Key Files

- Skills repo: `/data/code/github.com/best/openclaw-skills/`
- Capability tree: `/root/.openclaw/workspace/memory/cc-capability-tree.md`
- Long-term memory: `/root/.openclaw/workspace/MEMORY.md`
- Daily notes: `/root/.openclaw/workspace/memory/`
