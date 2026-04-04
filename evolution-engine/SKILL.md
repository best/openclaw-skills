---
name: evolution-engine
version: 2.0.1
description: "PCEC v4 — Data-driven skill evolution engine. Analyzes skill execution data to detect degradation, proactively optimize skills, predict issues, and verify improvements. Pairs with Dream for memory consolidation."
---

# Evolution Engine — PCEC v4

Periodic Cognitive Evolution Cycle. **Evolution = anti-entropy + anticipation.**

Core mission: make every skill and cron job measurably better over time. The same class of problem should never require human intervention twice, and degradation trends should be caught before they become failures.

## Design Philosophy

v1 accumulated genes. v2 waited for errors. v3 relied on human-intervention signals from daily logs. All three were reactive.

v4 is **data-driven**. The richest evolution signals are in execution metrics — duration trends, token efficiency, error patterns — not just in what humans complained about.

**Division of labor**: PCEC owns skill/cron evolution. Dream 🌙 owns memory consolidation. They share daily logs as a signal source but never modify each other's targets.

## Four-Phase Cycle

### Phase 1: Observe

Collect signals from three sources in priority order.

**1a. Execution data analysis**

```
cron action=list  →  all jobs: lastStatus, lastDurationMs, consecutiveErrors
cron action=runs jobId=<id>  →  recent runs: duration, tokens, status
```

For each skill-type cron (exclude heartbeat, balance-check, and other pure-ops jobs), analyze:

| Metric | How | Anomaly threshold |
|--------|-----|-------------------|
| Success rate | ok count in last 10 runs | <90% |
| Duration trend | last 5 avg vs historical avg | >50% growth |
| Token efficiency | total_tokens per run | >30% growth |
| Consecutive errors | from job metadata | >0 |

Anomalous jobs enter the evolve candidate list with specific metrics noted.

**1b. Daily logs**

```bash
cat ~/.openclaw/workspace/memory/$(date +%Y-%m-%d).md 2>/dev/null
cat ~/.openclaw/workspace/memory/$(date -d yesterday +%Y-%m-%d).md 2>/dev/null
```

Focus: human interventions, behavioral drift, repeated patterns. Secondary signal source.

**1c. Open trackers**

```bash
cat {baseDir}/gep/convergence-tracker.jsonl 2>/dev/null
```

Check open/regressed items.

**Signal classification:**

| Type | Description | Source | Priority |
|------|-------------|--------|----------|
| degradation | Execution metrics worsening (duration/token/success trend) | exec data | Highest |
| human-intervention | Human had to fix something that should be self-managed | daily logs | Highest |
| recurring-pattern | Same problem type appeared 2+ times | both | High |
| behavioral-drift | Acting inconsistently with established rules | daily logs | High |
| inefficiency | Wasting time, tokens, or human attention | exec data | Medium |
| system-health | Errors, timeouts, cron failures | exec data | Medium |

### Phase 2: Evolve

For each signal from Observe, take ONE concrete action. **Max 3 actions per cycle.** Priority order:

**1. Fix a skill**
- Edit SKILL.md / scripts in `/data/code/github.com/best/openclaw-skills/`
- Bump version (bugfix → patch, feature → minor)
- Update repo README.md + README_CN.md version tables
- git commit + push (format: `evolve: <skill> v<version> — <what>`)
- ⚠️ Only commit skill file changes (SKILL.md, scripts/, references/). Never commit gep/ data files.

**2. Fix a cron prompt**
- cron tool `action=update` with corrected payload
- Log what changed and why

**3. Optimize for efficiency**
- Token consumption growing → slim prompt or add lightContext
- Duration trending up → analyze bottleneck (network? model? logic complexity?)
- Reference file never read → clean up

**4. Predict & prevent**
- Duration trend approaching timeout → preemptively increase timeout or optimize
- Success rate slowly declining → investigate root cause before outbreak
- Any metric on a clear trajectory toward failure → intervene early

**5. Ground knowledge**
- Write to memory/reference/*.md
- Format: Symptom → Root Cause → Fix → Prevention

### No-signal behavior

When execution data and daily logs show no anomalies:

1. **Convergence check** — review open tracker items, advance clean-cycle counts
2. **Brief report and end** — no forced audit or make-work

This eliminates v3's mandatory-output-every-cycle problem.

### Phase 3: Verify

**3a. Quantitative health snapshot**

For each skill modified in Evolve, record before/after metrics in events.jsonl:

```json
{
  "skill": "feed-collect",
  "before": {"avg_duration_ms": 500000, "avg_tokens": 80000, "success_rate": 0.9},
  "after": null,
  "verified_at": null
}
```

Next cycle: fill `after` data and compare improvement.

**3b. Convergence tracking**

Maintain `{baseDir}/gep/convergence-tracker.jsonl`:
```json
{"id":"ct_NNN","ts":"ISO-8601","category":"degradation|human-intervention|recurring|drift|inefficiency|system-health","signal":"...","action":"...","status":"open","verify_after":"evt_NNN+2"}
```

- 2 clean cycles → `"status": "converged"`
- Recurred → `"status": "regressed"` — gets highest priority next cycle
- Terminal entries older than 3 cycles → archive to `convergence-archive.jsonl`

### Phase 4: Report

**4a. Write events.jsonl**

```json
{
  "id": "evt_NNN",
  "ts": "ISO-8601",
  "signals": {"execution_data": 2, "daily_log": 1, "tracker": 0},
  "actions": [{"type": "skill-fix|cron-fix|optimize|predict|knowledge", "target": "...", "summary": "..."}],
  "health": {"jobs_analyzed": 15, "healthy": 13, "degrading": 1, "failing": 1},
  "convergence": {"open": 1, "converged": 2, "regressed": 0}
}
```

Prune to 30 entries; archive older to `events-archive.jsonl`.

**Note:** All gep/ data files are local-only (gitignored). Do not attempt to git add/commit them.

**4b. Deliver to Discord**

Use message tool to send to the designated channel. Format:

With signals:
```
🔄 PCEC evt_NNN

📊 观测：分析 N 个 job — N 健康 / N 退化 / N 失败
  [退化详情]

🛠️ 进化（N actions）
  [action 列表]

✅ 验证
  [tracker 状态 + 前次修复效果]

💡 预测
  [趋势预警，如有]
```

No signals:
```
🔄 PCEC evt_NNN — 系统健康 ✅
📊 分析 N 个 job，全部健康。收敛追踪 N open。
```

## Work Items

For complex issues that need multiple cycles:
- Max 10 open items
- Must resolve within 3 cycles or close with reason
- Format in `{baseDir}/gep/work-items.jsonl`

## Anti-Entropy Lock

**Stability > Explainability > Reusability > Novelty**

Forbidden:
- Changes without evidence from observed signals or execution data
- Inventing problems to justify changes
- Creating GitHub issues autonomously
- Modifying workspace root files (AGENTS.md, TOOLS.md, SOUL.md) — human-owned
- `git add -A` (must explicitly specify files)
- Committing gep/ runtime data (events, trackers, work-items) — local-only, never push
- Running git commands inside workspace directory

## Success Metrics

1. **Convergence rate** — fixed once and stays fixed vs. regresses
2. **Prediction accuracy** — predicted degradations that actually occurred
3. **Skill health trend** — overall healthy-job ratio over time
