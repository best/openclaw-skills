---
name: evolution-engine
version: 0.3.0
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
- Repair always takes priority over innovate.

## Anti-Evolution Lock

Priority: Stability > Explainability > Reusability > Novelty

Forbidden:
- Summary-only cycles (must produce file changes)
- Creating GitHub issues autonomously
- Modifying files outside skills repo without reason
- "Feels right" as decision basis

## Stagnation Breaker

If 2 consecutive cycles produce no file changes:
- Force challenge a default assumption
- Or merge two similar capabilities
- Or audit an existing skill against real usage
