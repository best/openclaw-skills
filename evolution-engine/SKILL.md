---
name: evolution-engine
version: 1.2.0
description: "PCEC v3 — Anti-entropy self-evolution engine. Discovers behavioral issues from daily operations, self-corrects, and tracks convergence."
---

# Evolution Engine — PCEC v3

Periodic Cognitive Expansion Cycle. **Evolution = anti-entropy.**

Core mission: continuously review your own behavior, discover drift and problems, self-correct, and drive the system toward increasing order. The same class of problem should never require human intervention twice.

## Design Philosophy

PCEC v1 accumulated genes (pattern catalog). v2 waited for errors (passive repair). Both failed:
- v1 built knowledge only PCEC could see
- v2 skipped endlessly when the system was "clean"

v3 is **introspection-driven**. The most valuable evolution signals are not in error logs — they're in daily conversations where humans had to fix your problems.

## Three-Phase Cycle

Every cycle runs all three phases. **There is no skip.**

### Phase 1: Discover

Read these sources in order. Extract signals — anything that indicates a problem, inefficiency, or improvement opportunity.

**Primary: daily logs (richest signal source)**
```bash
cat ~/.openclaw/workspace/memory/$(date +%Y-%m-%d).md 2>/dev/null
cat ~/.openclaw/workspace/memory/$(date -d yesterday +%Y-%m-%d).md 2>/dev/null
```

Focus on:
- Moments where the human had to intervene to fix your behavior
- Decisions made about how things should work
- Mistakes you made and their root causes
- Patterns that repeated across multiple incidents
- Workarounds that should be permanent fixes

**Secondary: system health**
```bash
# Gateway errors — use pattern that excludes false positives from cron payload text
grep -P '^\d{4}-\d{2}.*\bERROR\b' /tmp/openclaw/openclaw-$(date +%Y-%m-%d).log 2>/dev/null | tail -20
```
Also: cron tool `action=list` → check `lastStatus` and `consecutiveErrors`

**Tertiary: open trackers**
```bash
cat {baseDir}/gep/convergence-tracker.jsonl 2>/dev/null
cat {baseDir}/gep/work-items.jsonl 2>/dev/null
```

**Signal classification:**

| Type | Description | Priority |
|------|-------------|----------|
| Human-intervention | Human had to fix something that should have been self-managed | Highest |
| Recurring-pattern | Same type of problem appeared 2+ times | High |
| Behavioral-drift | Acting inconsistently with established rules | High |
| Inefficiency | Wasting time, tokens, or human attention | Medium |
| System-health | Errors, timeouts, cron failures | Medium |
| Knowledge-gap | Repeatedly looking up the same thing | Low |

### Phase 2: Fix

For each signal, take ONE concrete action. **Max 3 actions per cycle.** Priority order:

**1. Fix a skill**
- Edit SKILL.md / scripts in `/data/code/github.com/best/openclaw-skills/`
- Bump version (bugfix → patch, feature → minor)
- Update repo `README.md` + `README_CN.md` version tables
- `git add -A && git commit -m "evolve: <skill> v<version> — <what>" && git push`

**2. Fix a cron prompt**
- Identify the specific prompt issue from daily logs
- Use cron tool `action=update` with corrected payload
- Log what changed and why

**3. Ground knowledge**
- Write to `memory/reference/*.md`
- Format: **Symptom → Root Cause → Fix → Prevention**
- Only if the knowledge isn't already documented

**4. Update behavioral guardrails**
- Add rules to relevant skill or reference doc to prevent recurrence
- Must be specific and actionable, not vague principles

**5. Create work item**
- For complex issues that can't be resolved in one cycle
- Must resolve within 3 cycles

### Phase 3: Verify

Track whether fixes actually work.

**Update convergence tracker** (`{baseDir}/gep/convergence-tracker.jsonl`):
```json
{"id":"ct_NNN","ts":"ISO-8601","category":"human-intervention|recurring|drift|inefficiency|system-health","signal":"what was found","action":"what was done","status":"open","verify_after":"evt_NNN+3"}
```

**Check existing trackers:**
- Same category of problem hasn't recurred for 3+ cycles → `"status": "converged"`
- Recurred → `"status": "regressed"` — the fix wasn't sufficient, needs deeper root cause analysis
- Regressed items get highest priority in next cycle

### When Daily Logs Have No New Signals

Even when everything is quiet, do one of:

1. **Audit a skill** — pick one from the repo, check actual usage in recent session logs, look for outdated instructions / missing guards / token waste
2. **Review convergence tracker** — verify "converged" items haven't regressed
3. **Proactive improvement** — find one thing that works but could work better

Every cycle produces output.

## Event Log

Append to `{baseDir}/gep/events.jsonl`:
```json
{"id":"evt_NNN","ts":"ISO-8601","signals_found":2,"actions":[{"type":"skill-fix|cron-fix|knowledge|guardrail|audit","target":"...","summary":"..."}],"convergence":{"open":3,"converged":5,"regressed":0}}
```

Prune to 30 entries; archive older to `events-archive.jsonl`.

## Work Items

Temporary tracker for complex issues. Same rules as v2:
- Max 10 open items
- Must resolve within 3 cycles or close with reason
- Resolution always points to a concrete change

Format in `{baseDir}/gep/work-items.jsonl`:
```json
{"id":"wi_NNN","ts":"ISO-8601","signal":"what was observed","status":"open","target":"...","cycle_created":"evt_NNN","cycle_limit":"evt_NNN+3"}
```

## Anti-Entropy Lock

**Stability > Explainability > Reusability > Novelty**

Forbidden:
- Empty skips — every cycle must produce substantive output
- Self-referential knowledge accumulation
- Changes without evidence from observed signals
- "Feels right" as decision basis
- Inventing problems to justify changes
- Creating GitHub issues autonomously
- Modifying workspace root files (AGENTS.md, TOOLS.md, SOUL.md) — human-owned

## Success Metric

**Convergence rate** — the ratio of issues that get fixed once and stay fixed vs. issues that regress. PCEC succeeds when the human spends less time fixing agent problems over time.
