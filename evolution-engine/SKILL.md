---
name: evolution-engine
version: 1.0.0
description: "PCEC self-evolution engine. Iterates skills and grounds operational knowledge from runtime signals."
---

# Evolution Engine — PCEC v2

Periodic Cognitive Expansion Cycle. Autonomous evolution through **skill iteration** and **knowledge grounding**.

## Core Principle

**Every evolution must land somewhere visible.** Three valid outputs, in priority order:

1. **Skill improvement** — modify SKILL.md, scripts, or templates in the skills repo (highest value: auto-loaded by all sessions)
2. **Knowledge grounding** — write to `memory/reference/*.md` (searchable by all sessions via memory_search)
3. **Work item** — temporary tracker for complex issues (must resolve within 3 cycles)

Invalid output: adding to a self-referential knowledge base that only PCEC can see.

## Data Sources

| Source | Command | What to look for |
|--------|---------|------------------|
| Gateway errors | `grep ERROR /tmp/openclaw/openclaw-$(date +%Y-%m-%d).log \| tail -30` | Error patterns, skill failures |
| Cron health | cron tool `action=list` | Failed jobs, slow jobs (>5min) |
| Recent sessions | `ls -t ~/.openclaw/agents/main/sessions/*.jsonl \| head -3` + grep | Skill invocation failures |
| Daily memory | `cat ~/.openclaw/workspace/memory/$(date +%Y-%m-%d).md` | User feedback, pain points |
| Skills repo | `/data/code/github.com/best/openclaw-skills/` | Current skill code |
| Work items | `{baseDir}/gep/work-items.jsonl` | Open items from previous cycles |
| Reference docs | `~/.openclaw/workspace/memory/reference/` | Already documented knowledge |

## PCEC Cycle

### Step 1: Quick Triage (exit fast if clean)

```bash
ERROR_COUNT=$(grep -c ERROR /tmp/openclaw/openclaw-$(date +%Y-%m-%d).log 2>/dev/null || echo 0)
echo "Errors today: $ERROR_COUNT"
```

Also: cron tool `action=list` → check `lastStatus` and `consecutiveErrors`.
Also: `cat {baseDir}/gep/work-items.jsonl` → check for open items.

**If all clean** (0 new errors, 0 cron failures, 0 open work items):
→ Log skip to `events.jsonl` and exit immediately. Target: <30s, <20k tokens.

### Step 2: Signal Classification (only if Step 1 found signals)

Read the actual error messages. For each signal, classify:

| Classification | Criteria | Action |
|---------------|----------|--------|
| **Skill-fixable** | Error relates to a skill's behavior or code | Fix the skill |
| **Knowledge gap** | Useful pattern not yet in reference docs | Write to `memory/reference/` |
| **Already documented** | Pattern exists in reference docs | Skip (system is working as expected) |
| **Transient** | Provider 503, network blip, one-off | Skip |
| **Complex** | Multi-step, needs investigation | Create work item |

To check if already documented:
```bash
grep -l "keyword" ~/.openclaw/workspace/memory/reference/*.md 2>/dev/null
```

### Step 3: Act (one action per cycle, priority order)

**Priority 1: Fix a skill**
1. Read the affected skill's SKILL.md and related files
2. Identify root cause from signal data
3. Fix it (edit code, improve prompts, add error handling)
4. Bump version in SKILL.md frontmatter (bugfix → patch, feature → minor)
5. Update repo `README.md` + `README_CN.md` version tables
6. Commit: `git add -A && git commit -m "evolve: <skill-name> v<version> — <what changed>" && git push`

**Priority 2: Ground knowledge**
1. Check if `memory/reference/openclaw-troubleshooting.md` or other reference docs cover it
2. If not documented, add a concise entry: **Symptom → Cause → Fix**
3. Commit reference doc changes to skills repo if applicable, otherwise just write to workspace

**Priority 3: Audit a skill** (when system has low-priority signals)
1. Pick one skill from the repo (prefer least-recently-audited)
2. Check recent session logs for how it was actually used
3. Look for: outdated instructions, missing error handling, token waste, stale paths
4. Improve if issues found, otherwise note "audited, healthy" in event log

**Priority 4: Resolve open work items**
- Items >3 cycles old → resolve or close with reason
- Resolution must point to concrete output: "fixed skill X v1.2.3" or "documented in reference/Y"

### Step 4: Log Event

Append to `{baseDir}/gep/events.jsonl`:
```json
{"id": "evt_NNN", "ts": "ISO-8601", "result": "skill-fix|knowledge-ground|skill-audit|skip", "target": "skill:name|ref:filename|none", "summary": "one line"}
```

Prune to 20 entries; archive older to `events-archive.jsonl`.

## Work Items (temporary issue tracker)

Replaces the old gene system. Work items are **temporary** — they track issues, not knowledge.

Format in `{baseDir}/gep/work-items.jsonl`:
```json
{"id": "wi_NNN", "ts": "ISO-8601", "signal": "what was observed", "status": "open", "target": "skill:name|ref:name|investigate", "cycle_created": 94, "cycle_limit": 97}
```

Rules:
- Max 10 open items at any time
- Must resolve within 3 cycles or close with reason
- Resolution always points to a concrete change
- Closed items: change `status` to `"resolved"` or `"closed"`, add `"resolution": "what was done"`
- No permanent accumulation — if it's worth keeping, it belongs in a reference doc or skill improvement

## Strategy Priority

repair skill > ground knowledge > audit skill > create skill > skip

## Anti-Evolution Lock

Priority: **Stability > Explainability > Reusability > Novelty**

Forbidden:
- Accumulating permanent self-referential knowledge (no genes.json-style accumulation)
- Modifying skills without evidence from actual usage/errors
- "Feels right" as decision basis
- Inventing problems to justify changes
- Creating GitHub issues autonomously
- Modifying workspace root files (AGENTS.md, TOOLS.md, SOUL.md) — these are human-owned

## Cost Discipline

- Clean system → exit in Step 1 (target: <30s, <20k tokens)
- Active evolution → target: <3min, <80k tokens
- Don't read large files unless signals point to them
- One skill audit per cycle max
- Prefer `grep` and `tail` over full file reads

## Migration Note (v1 → v2)

PCEC v1 (0.1.0–0.4.0) focused on gene accumulation — cataloging error patterns in `genes.json`. This produced 32 genes over 93 cycles, but most knowledge was only visible to PCEC itself.

PCEC v2 (1.0.0) shifts focus to **skill iteration** and **knowledge grounding**:
- Old genes → migrated to `memory/reference/openclaw-troubleshooting.md` and `memory/reference/discord-troubleshooting.md`
- Old gene/capsule files → archived in `gep/archive/`
- Gene system → replaced by temporary work items
