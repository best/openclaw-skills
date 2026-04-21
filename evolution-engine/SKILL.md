---
name: evolution-engine
version: 3.0.0-preview
description: "PCEC — 受控进化引擎。从 Cron 执行数据与 Session Transcript 双维度检测问题，强制证据链诊断，产出修复草案经审核后执行。自主进化，但有监管。适用于：定期系统健康检查、Cron 任务诊断、技能退化检测、系统级趋势预警。"
---

# Evolution Engine — PCEC

受控的自主进化引擎。周期性检测系统问题、诊断根因、提出进化方案——所有修改操作必须经过审核后才执行。

> 职责边界见 `references/responsibility-boundary.md`（PCEC / Dream / Heartbeat 分工）。

## 三条铁律

### 铁律 1：证据链（强制）

每个诊断必须有 Session Transcript 支撑：

1. `cron action=runs` → 发现异常 run（元数据触发）
2. `sessions_history(sessionKey, includeTools=true)` → 读实际发生了什么
3. 读完 transcript 后才下诊断结论

禁止仅凭 duration/token/status 元数据做诊断。

### 铁律 2：只写草案（强制）

不直接修改任何文件。所有变更以草案形式提交审核：

- ❌ 编辑 SKILL.md / 修改 cron prompt / git 操作
- ✅ 写修复草案到 `{baseDir}/gep/drafts/`
- ✅ 通过 Discord 投递报告（含草案摘要）

### 铁律 3：无信号静默（强制）

全部 job 健康 → 快速扫描后静默结束。不发报告、不写 events.jsonl、不输出任何内容。

## 执行流程

### 有异常时：完整周期

```
检测 → 调查(读Session) → 草案 → 报告
```

#### Step 1：检测

```bash
cron action=list                                    # 全量 job
cron action=runs jobId=<id>                          # 每个 skill 类 job 最近 10 次
```

异常阈值（触达任一即进入调查）：

| 指标 | 阈值 |
|------|------|
| 成功率（近 10 次） | <90% |
| 耗时趋势（近 5 次均值 vs 历史） | 增长 >50% |
| 连续错误 | ≥1 |
| 超时率（近 10 次） | ≥20% |

**排除以下类别**（瞬态失败不代表技能问题）：
- 系统巡检类（心跳）
- 余额监控类（各 provider 余额检查）
- 报告类（费用账单/周报）
- 通知类（天气播报）

#### Step 2：调查 — 读 Session Transcript

```bash
# 异常 session（必须 includeTools=true）
sessions_history(sessionKey="<异常run的sessionKey>", limit=1, includeTools=true)

# 前一次成功 run（对比用）
sessions_history(sessionKey="<前次成功sessionKey>", limit=1)
```

证据模式对照表：

| 症状 | Transcript 中的特征 |
|------|-------------------|
| 模型幻觉 | 编造不存在的命令或文件 |
| Prompt 误解 | 跳过步骤或执行错误工作流 |
| API/限速 | 明确的 provider 错误信息 |
| Token 溢出 | Context 过大导致截断 |
| 逻辑循环 | 重复相同工具调用链 |
| 脚本失败 | exec 非零退出 + stderr |
| 投递失败 | message 工具报错但任务完成 |

输出置信度：high / medium / low。low → 不出草案，标记"需更多数据"。

#### Step 3：草案

写入 `{baseDir}/gep/drafts/YYYY-MM-DD_<名称>.json`：

```json
{
  "id": "draft_NNN",
  "created_at": "ISO-8601",
  "job_id": "...",
  "job_name": "...",
  "evidence": { /* 来自 Step 2 */ },
  "diagnosis": "基于 transcript 的根因",
  "proposed_fix": {
    "type": "skill-patch|cron-prompt-patch|config-change|new-constraint",
    "target_file": "相对路径/目标文件",
    "description": "改什么、为什么",
    "risk_level": "safe|moderate|risky",
    "side_effects": "可能的副作用"
  },
  "status": "pending-review"
}
```

质量标准：
1. `target_file` 是具体已有文件路径
2. `description` 引用目标文件中的具体位置
3. risky = 涉及 T0 文件 / 凭证 / git / 其他 cron 配置
4. `side_effects` 至少一条
5. 一案一草，不批量

#### Step 4：报告

Discord 投递格式：

```
🔄 PCEC 检测报告 YYYY-MM-DD HH:MM

📊 扫描：N 个 job — N 健康 / N 异常

🔍 调查
**1. [Job 名称]**
  症状：[元数据异常]
  证据：[transcript 关键发现，1-2 句]
  诊断：[根因] · 置信度：高/中/低

📝 草案（N 个）
  DRAFT draft_NNN: [摘要] — 风险: 低/中/高 → 待审核
```

### 无异常时：静默

`cron action=list` 确认全绿 → 直接结束。零输出。

## 安全边界

**禁止：**
- 文件修改（SKILL.md / scripts / cron prompts / config）
- git add/commit/push（任何场景）
- 无 transcript 就做诊断
- 无异常时发报告
- GitHub Issue / PR
- 修改 workspace 根文件（AGENTS.md / TOOLS.md / SOUL.md / USER.md）
- workspace 内运行 git 命令
- 提交 gep/ 数据到 git

**允许：**
- 读任意文件
- 写 `{baseDir}/gep/drafts/` 和 `{baseDir}/gep/events.jsonl`（仅异常时，≤30 条）
- `message` 工具发送
- `cron action=list` / `cron action=runs`（只读）
