---
name: evolution-engine
version: 0.4.0
description: "PCEC self-evolution engine with GEP protocol. Analyzes runtime history to drive capability evolution."
---

# Evolution Engine — PCEC with GEP Protocol

Periodic Cognitive Expansion Cycle. Autonomous self-evolution through runtime analysis.

## Data Sources (read via exec/read tools)

| Source | Path | Content |
|--------|------|---------|
| Session history | `~/.openclaw/agents/main/sessions/*.jsonl` | All conversation records |
| Cron runs | `~/.openclaw/cron/runs/*.jsonl` | Cron execution history |
| Gateway logs | `/tmp/openclaw/openclaw-*.log` | Runtime errors |
| Memory files | `~/.openclaw/workspace/memory/` | Daily notes, capability tree |
| Long-term memory | `~/.openclaw/workspace/MEMORY.md` | Curated lessons |
| Skills repo | `/data/code/github.com/best/openclaw-skills/` | Current skills |
| GEP assets | `./gep/genes.json, capsules.json, events.jsonl` | Evolution state |

## PCEC Cycle

### 1. Signal Extraction
Scan recent data for evolution signals:
```bash
# Recent session errors
grep -r "error\|failed\|retry" ~/.openclaw/agents/main/sessions/*.jsonl --include="*.jsonl" -l | tail -5

# Cron failures
tail -50 ~/.openclaw/cron/runs/*.jsonl | grep '"error"'

# Gateway errors (today)
grep "ERROR" /tmp/openclaw/openclaw-$(date +%Y-%m-%d).log | tail -20

# Recent memory for patterns
cat ~/.openclaw/workspace/memory/$(date +%Y-%m-%d)*.md
```

### 2. Gene Matching
Read `gep/genes.json`. Check if any existing Gene matches the signals.
- Match found → apply Gene strategy
- No match → abstract new Gene from signal

### 3. Evolution Action (pick one)

**A. New/Updated Skill**
- Write SKILL.md to skills repo
- Symlink if new
- Update README.md + README_CN.md versions

**B. New Gene**
- Abstract the pattern: trigger → strategy
- Add to `gep/genes.json`

**C. New Capsule**
- Encode a multi-step solution that worked
- Add to `gep/capsules.json`

**D. No Evolution Needed (idle)**
- Valid when: no new errors, all signals match existing genes, no fragile patterns found
- Append a skip event to `events.jsonl` with result `"skip"` and brief context
- This counts as a file change (events.jsonl is updated)
- 3+ consecutive skips triggers the Stagnation Breaker

### 4. Commit
```bash
cd /data/code/github.com/best/openclaw-skills
git add -A && git commit -m "evolve: <description>" && git push
```
Append EvolutionEvent to `gep/events.jsonl`.
Update capability tree if needed.

## Evolution Strategy

Assess current state to pick strategy:
- **repair** — errors detected in logs/cron → fix first
- **harden** — no errors but fragile patterns → add robustness
- **innovate** — stable state → identify new capability opportunities
- **skip** — genuinely clean, all signals covered → log and exit
- Priority: repair > harden > innovate > skip

## Idle Period Protocol

When the system is stable and no new signals exist:
1. Confirm: all gateway errors match existing genes (no new patterns)
2. Confirm: no cron failures since last cycle
3. Confirm: no new session errors or user-reported issues
4. If all three hold → this is a genuine idle period
5. Log a skip event and exit — don't force low-value changes

**Cost awareness:** Each PCEC cycle costs LLM tokens (Opus-tier). Idle cycles should be fast and cheap. The value of PCEC is in catching real issues, not in producing changes for the sake of compliance.

**Idle period work (optional, in lieu of skip):**
- Prune events.jsonl if approaching 30 lines (per gene_prune_unbounded_sections)
- Audit an existing skill against recent real usage
- Review gene pool for merges or obsolescence
- Update capability tree or documentation

## Anti-Evolution Lock

Priority: Stability > Explainability > Reusability > Novelty

Forbidden:
- Creating GitHub issues autonomously
- Modifying files outside skills repo without reason
- "Feels right" as decision basis
- Inventing problems to justify changes

## Stagnation Breaker

If 3 consecutive cycles produce skip events:
- Force challenge a default assumption
- Or merge two similar capabilities
- Or audit an existing skill against real usage
