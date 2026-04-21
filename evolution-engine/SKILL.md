---
name: evolution-engine
version: 3.0.0
description: "PCEC v5 — Problem Observation Station. Detects issues from cron execution data AND session transcripts (not just metadata), produces fix drafts for human review. Read-only: never auto-modifies files. Use when: periodic system health check, cron job diagnosis, skill degradation detection."
---

# Evolution Engine — PCEC v5

**Problem Observation Station, not an autonomous evolution engine.**

v4 tried to be a self-driving evolution loop — it failed because LLMs can't reliably diagnose from metadata alone, and autonomous file modifications introduce risk without proportional value.

v5's job is simpler: **find real problems, prove them with evidence, propose fixes for review.**

## Division of Labor

| Component | Owns | Doesn't touch |
|-----------|------|---------------|
| PCEC v5 | Problem detection + fix proposals | Memory consolidation |
| Dream 🌙 | T0/T1/T2 memory maintenance | Skill/cron health |
| Heartbeat | System health snapshot | Long-term trends |

PCEC and Dream share daily logs as signal source but never modify each other's targets.

## Three Hard Rules

### Rule 1: Evidence Chain (强制)

**Every diagnosis must be backed by session transcript content.**

Workflow:
1. `cron action=runs jobId=<id>` → find anomalous runs (metadata)
2. For each anomaly → `sessions_history(sessionKey=<run's sessionKey>, limit=1, includeTools=true)` → read what actually happened
3. Only after reading session content → diagnose root cause

**Forbidden:** Diagnosing from duration/token/status metadata alone. Metadata triggers investigation; transcripts confirm diagnosis.

### Rule 2: Read-Only (强制)

**PCEC never directly modifies any file.**

- ❌ No editing SKILL.md
- ❌ No updating cron prompts via `cron action=update`
- ❌ No git add/commit/push
- ✅ Write fix drafts to `{baseDir}/gep/drafts/`
- ✅ Deliver reports with draft summaries via Discord

Drafts are proposals. Execution requires approval (see Approval Flow).

### Rule 3: No-Signal Silence (强制)

When all jobs are healthy with zero anomalies:

- **Do not** run full 4-phase cycle
- **Do not** write events.jsonl entries
- **Do not** send "系统健康" reports to Discord
- **Do**: quick metadata scan (job list + lastStatus), then silently end

This eliminates ~500K tokens/day of no-value output.

## Execution Modes

### Mode A: Full Cycle (有信号时)

Triggered when: at least one job shows anomaly in metadata scan.

```
Detect → Investigate → Draft → Report
```

#### Step 1: Detect — Metadata Scan

```bash
# Get all jobs
cron action=list

# For each skill-type job (exclude heartbeat, balance-checks, pure-ops):
cron action=runs jobId=<id>   # recent 10 runs
```

Anomaly thresholds:

| Metric | Threshold |
|--------|-----------|
| Success rate (last 10) | <90% |
| Duration trend (last 5 avg vs historical) | >50% growth |
| Consecutive errors | ≥1 |
| Timeout rate (last 10) | ≥20% |

Jobs passing all thresholds → skip. Jobs failing any → enter Investigate.

**Scope**: Only analyze skill/logic cron jobs. Exclude:
- 心跳巡检 (heartbeat)
- OpenRouter/DeepRouter/秘塔余额监控 (pure-ops)
- 每日费用账单 / 每周费用周报 (reporting)
- 早安天气播报 (notification)

These are operational jobs where transient failures don't indicate skill problems.

#### Step 2: Investigate — Session Transcript Analysis (核心)

For each flagged job, gather evidence:

```bash
# 1. Read the most recent anomalous session's full history
sessions_history(sessionKey="<job's sessionKey>", limit=1, includeTools=true)

# 2. If error/timeout, also read the previous successful run for comparison
sessions_history(sessionKey="<job's previous success sessionKey>", limit=1, includeTools=false)
```

**What to look for in transcripts:**

| Symptom | Evidence Pattern in Transcript |
|---------|-------------------------------|
| Model hallucination | Agent invented commands/files that don't exist |
| Prompt misunderstanding | Agent skipped steps or did wrong workflow |
| API/rate-limit issue | Clear error messages from provider, not agent logic failure |
| Token overflow | Context too large for model, output truncated |
| Logic loop | Agent repeating same tool calls in cycles |
| Script failure | exec command returned non-zero with stderr |
| Message delivery failure | message tool returned error but task completed |

**Output per investigated job:**

```json
{
  "job_id": "...",
  "job_name": "...",
  "anomaly_type": "degradation|failure|timeout|drift",
  "evidence": {
    "metadata": {"lastStatus": "...", "lastDurationMs": N, "consecutiveErrors": N},
    "transcript_summary": "What actually happened in the session (from sessions_history)",
    "comparison": "How this differs from normal runs (if available)"
  },
  "diagnosis": "Root cause based on transcript content, NOT guessed from metadata",
  "confidence": "high|medium|low"
}
```

If confidence = "low" after reading transcripts → mark as "needs more data", do NOT draft a fix.

#### Step 3: Draft — Fix Proposal (只写不改)

For each high/medium confidence diagnosis, write a draft:

**File**: `{baseDir}/gep/drafts/YYYY-MM-DD_<short-name>.json`

```json
{
  "id": "draft_NNN",
  "created_at": "ISO-8601",
  "job_id": "...",
  "job_name": "...",
  "evidence": { /* from Investigate */ },
  "diagnosis": "...",
  "proposed_fix": {
    "type": "skill-patch|cron-prompt-patch|config-change|new-constraint",
    "target_file": "relative/path/to/file",  // which file would be modified
    "description": "What to change and why, in plain Chinese",
    "diff_idea": "Conceptual diff (not actual diff, since we're not editing)",
    "risk_level": "safe|moderate|risky",
    "side_effects": "What could go wrong"
  },
  "status": "pending-review"
}
```

**Draft quality standards:**

1. `target_file` must be a specific existing file path
2. `description` must reference specific lines or sections in the target file
3. `risk_level` = "risky" if the change touches: T0 files (MEMORY/SOUL/USER/TOOLS), auth credentials, git operations, or other cron job configs
4. `side_effects` must include at least one possible negative outcome
5. One draft per problem — no batched "cleanup" drafts

#### Step 4: Report — Discord Delivery

Send structured report to PCEC channel via `message` tool.

**With drafts:**

```
🔄 PCEC 检测报告 YYYY-MM-DD HH:MM

📊 扫描：N 个 job — N 健康 / N 异常

🔍 调查（N 个异常 job）

**1. [Job Name]**
  症状：[anomaly from metadata]
  证据：[key finding from session transcript, 1-2 sentences]
  诊断：[root cause]
  置信度：高/中/低

📝 修复草案（N 个）
  DRAFT draft_NNN: [one-line summary] — 风险: 低/中/高
  → 等待审核后执行

💡 观察（可选）
  [trend warnings that don't need immediate action]
```

**No anomalies detected (shouldn't reach here if silent-skip works, but just in case):**

```
🔄 PCEC 快速扫描 YYYY-MM-DD HH:MM — 全部正常，无异常信号
```

Note: This should rarely be sent. Most no-signal cycles should silently end in Mode B.

### Mode B: Lightweight Scan (无信号时)

Triggered when: all jobs pass anomaly thresholds in Step 1.

```bash
# Quick check only:
cron action=list   # verify all enabled jobs show lastStatus=ok, consecutiveErrors=0
```

If all green → **silently end. No output, no events.jsonl, no Discord message.**

If any red found during quick check → upgrade to Mode A for those jobs.

## Draft Approval Flow

Drafts written to `{baseDir}/gep/drafts/` require approval before execution:

1. PCEC writes draft + sends report with summary
2. **Approval options:**
   - **Main session (霄晗)** reviews and executes: reads draft → validates → applies fix → updates draft status to `applied`
   - **昊辰** can review draft from Discord report and instruct execution
3. After execution: update draft `status` to `"applied"` with `applied_at` timestamp and `applied_by`
4. Rejected drafts: update status to `"rejected"` with `reason`

**PCEC never self-approves or auto-executes its own drafts.**

## Anti-Entropy Lock

**Safety > Autonomy > Activity**

Forbidden:
- Any file modification (SKILL.md, scripts, cron prompts, config)
- `git add/commit/push` under any circumstances
- Diagnosing without session transcript evidence
- Sending reports when there's nothing to report
- Creating GitHub issues or PRs
- Modifying workspace root files (AGENTS.md, TOOLS.md, SOUL.md, USER.md)
- Running git commands inside workspace directory
- Committing gep/ runtime data (drafts, events) — local-only, never push

Allowed:
- Reading any file (skills, logs, session histories, configs)
- Writing to `{baseDir}/gep/drafts/` only
- Writing `{baseDir}/gep/events.jsonl` (only for anomaly cycles, pruned to 30)
- Sending messages via `message` tool
- `cron action=list` and `cron action=runs` (read-only)

## Schedule & Frequency

Configured externally via cron job: `0 1,9,17 * * *` (every 8 hours).

Each execution independently chooses Mode A or Mode B based on detected signals.
Expected distribution: mostly Mode B (silent), occasional Mode A (full report).
