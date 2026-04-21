---
name: evolution-engine
version: 3.0.0-preview
description: "PCEC v5 — 问题观测站。从 Cron 执行数据 + Session Transcript 双维度检测问题，产出只读修复草案供审核。不自修改任何文件。适用于：定期系统健康检查、Cron 任务诊断、技能退化检测。"
---

# Evolution Engine — PCEC v5

**问题观测站，不是自主进化引擎。**

v4 试图做自主进化闭环——失败了，因为 LLM 无法仅凭元数据可靠诊断，且自主文件修改引入的风险与收益不成比例。

v5 的职责更纯粹：**找到真问题，用证据证明，提出修复方案等审核。**

## 职责分工

| 组件 | 负责什么 | 不碰什么 |
|------|----------|---------|
| PCEC v5 | 问题检测 + 修复提案 | 记忆整合 |
| Dream 🌙 | T0/T1/T2 记忆维护 | 技能/Cron 健康 |
| Heartbeat | 系统健康快照 | 长期趋势 |

PCEC 和 Dream 共享 daily logs 作为信号源，但永远不修改对方的目标。

## 三条铁律

### 铁律 1：证据链（强制）

**每个诊断必须有 Session Transcript 内容支撑。**

流程：
1. `cron action=runs jobId=<id>` → 发现异常 run（元数据）
2. 对每个异常 → `sessions_history(sessionKey=<run的sessionKey>, limit=1, includeTools=true)` → 读实际发生了什么
3. 读完 session 内容后 → 才能下诊断结论

**禁止：** 仅凭 duration/token/status 元数据做诊断。元数据触发调查；transcript 确认诊断。

### 铁律 2：只读不写（强制）

**PCEC 永远不直接修改任何文件。**

- ❌ 不编辑 SKILL.md
- ❌ 不通过 `cron action=update` 修改 prompt
- ❌ 不执行 git add/commit/push
- ✅ 只写修复草案到 `{baseDir}/gep/drafts/`
- ✅ 通过 Discord 投递报告（附带草案摘要）

草案是提案。执行需要通过审核流（见下方「发布与审核规范」）。

### 铁律 3：无信号静默（强制）

当所有 job 全部健康、零异常时：

- **不跑**完整检测流程
- **不写** events.jsonl 条目
- **不发**"系统健康"报告到 Discord
- **做**：快速元数据扫描（job list + lastStatus），然后静默结束

这消除了每天 ~500K tokens 的无价值输出。

## 执行模式

### 模式 A：完整周期（有信号时）

触发条件：至少一个 job 在元数据扫描中显示异常。

```
检测 → 调查 → 草案 → 报告
```

#### Step 1：检测 — 元数据扫描

```bash
# 获取所有 job
cron action=list

# 对每个技能类 job（排除心跳/余额监控/纯运维类）：
cron action=runs jobId=<id>   # 最近 10 次 run
```

异常阈值：

| 指标 | 阈值 |
|------|------|
| 成功率（最近 10 次） | <90% |
| 耗时趋势（近 5 次均值 vs 历史） | 增长 >50% |
| 连续错误次数 | ≥1 |
| 超时率（最近 10 次） | ≥20% |

全部通过的 job → 跳过。触达阈值的 → 进入调查。

**排除范围**（纯运维 job，瞬态失败不代表技能问题）：
- 心跳巡检
- OpenRouter / DeepRouter / 秘塔余额监控
- 每日费用账单 / 每周费用周报
- 早安天气播报

#### Step 2：调查 — Session Transcript 分析（核心步骤）

对每个标记异常的 job，收集证据：

```bash
# 1. 读取最近一次异常 session 的完整历史
sessions_history(sessionKey="<job的sessionKey>", limit=1, includeTools=true)

# 2. 如果是错误/超时，再读前一次成功 run 作对比
sessions_history(sessionKey="<job前一次成功的sessionKey>", limit=1, includeTools=false)
```

**在 Transcript 中寻找的证据模式：**

| 症状 | Transcript 中的证据特征 |
|------|------------------------|
| 模型幻觉 | Agent 编造了不存在的命令或文件 |
| Prompt 误解 | Agent 跳过步骤或执行了错误的工作流 |
| API/限速 | 明确的 provider 错误信息，非 Agent 逻辑失败 |
| Token 溢出 | Context 过大导致输出截断 |
| 逻辑循环 | Agent 重复调用相同工具调用链 |
| 脚本失败 | exec 返回非零退出码 + stderr |
| 消息投递失败 | message 工具返回错误但任务本身完成 |

**每个被调查 job 的输出：**

```json
{
  "job_id": "...",
  "job_name": "...",
  "anomaly_type": "degradation|failure|timeout|drift",
  "evidence": {
    "metadata": {"lastStatus": "...", "lastDurationMs": N, "consecutiveErrors": N},
    "transcript_summary": "Session 中实际发生了什么（来自 sessions_history）",
    "comparison": "与正常 run 的差异（如有）"
  },
  "diagnosis": "基于 transcript 内容的根因诊断，不是从元数据猜测的",
  "confidence": "high|medium|low"
}
```

confidence = "low" → 标记为"需更多数据"，不出草案。

#### Step 3：草案 — 修复提案（只写不改）

对每个高/中等置信度诊断，写一份草案：

**文件路径**：`{baseDir}/gep/drafts/YYYY-MM-DD_<简短名称>.json`

```json
{
  "id": "draft_NNN",
  "created_at": "ISO-8601",
  "job_id": "...",
  "job_name": "...",
  "evidence": { /* 来自调查阶段 */ },
  "diagnosis": "...",
  "proposed_fix": {
    "type": "skill-patch|cron-prompt-patch|config-change|new-constraint",
    "target_file": "相对路径/目标文件",
    "description": "改什么、为什么，用中文描述",
    "diff_idea": "概念性 diff（不是实际 diff，因为不编辑文件）",
    "risk_level": "safe|moderate|risky",
    "side_effects": "可能有什么副作用"
  },
  "status": "pending-review"
}
```

**草案质量标准：**
1. `target_file` 必须是具体的已有文件路径
2. `description` 必须引用目标文件中的具体行或段落
3. `risk_level` = "risky" 的条件：涉及 T0 文件（MEMORY/SOUL/USER/TOOLS）、认证凭证、git 操作、或其他 cron 配置
4. `side_effects` 必须包含至少一种可能的负面后果
5. 一个草案对应一个问题——不允许批量"清理"式草案

#### Step 4：报告 — Discord 投递

通过 `message` 工具发送结构化报告到 PCEC 频道。

**有草案时：**

```
🔄 PCEC 检测报告 YYYY-MM-DD HH:MM

📊 扫描：N 个 job — N 健康 / N 异常

🔍 调查（N 个异常 job）

**1. [Job 名称]**
  症状：[来自元数据的异常]
  证据：[session transcript 中的关键发现，1-2 句]
  诊断：[根因]
  置信度：高/中/低

📝 修复草案（N 个）
  DRAFT draft_NNN: [一句话摘要] — 风险: 低/中/高
  → 待审核后执行

💡 观察（可选）
  [不需要立即处理的趋势预警]
```

**无异常时**（正常不应到达这里，防兜底）：

```
🔄 PCEC 快速扫描 YYYY-MM-DD HH:MM — 全部正常，无异常信号
```

### 模式 B：轻量扫描（无信号时）

触发条件：Step 1 所有 job 通过异常阈值。

```bash
# 仅快速检查：
cron action=list   # 确认所有 enabled job 的 lastStatus=ok, consecutiveErrors=0
```

全绿 → **静默结束。无输出、无 events.jsonl、无 Discord 消息。**

发现红色 → 对该 job 升级到模式 A。

## 发布与审核规范

### 版本生命周期

```
preview → review → release
   ↑         │
   └─────────┘
     可多次迭代
```

1. **preview**：功能开发完成后的预览版本，标记为 `vX.Y.Z-preview`
2. **review**：由 OpenClaw 主 session 或人工审核，检查：
   - 铁律是否完整（证据链 / 只读 / 静默）
   - 草案格式是否规范
   - 排除范围是否合理
   - 是否包含个人化信息（公开仓库禁忌）
   - 与其他 skill 的职责边界是否清晰
3. **release**：审核通过后去掉 `-preview` 后缀，git commit + push 正式版

### 审核清单

发布正式版前必须逐项确认：

- [ ] 三条铁律在 SKILL.md 中明确写出且有强制语义
- [ ] 不含任何个人名称、个人环境信息、内部频道 ID
- [ ] Draft 审批流不依赖特定人员身份（用角色描述）
- [ ] 无信号时的行为是静默结束（不是发"系统健康"）
- [ ] 排除范围明确列出了不该分析的 job 类型
- [ ] `sessions_history` 作为诊断前置条件被强调
- [ ] Forbidden 列表包含 git 操作和文件修改
- [ ] README / README_CN.md 版本号同步更新

### 草案审批流

PCEC 写入 `{baseDir}/gep/drafts/` 的修复草案需要审批才能执行：

1. PCEC 写入草案 + 发送报告（含摘要）
2. **审批方**：OpenClaw 主 session 或系统管理员
3. 审批后执行：读草案 → 验证 → 应用修复 → 更新草案 status 为 `applied`
4. 驳回：更新 status 为 `"rejected"` 并填写 `reason`

**PCEC 永远不自审自执自己的草案。**

## 反熵锁

**安全 > 自主性 > 活跃度**

禁止事项：
- 任何文件修改（SKILL.md、scripts、cron prompts、配置）
- `git add/commit/push`（任何场景）
- 不读 session transcript 就做诊断
- 没问题时发报告
- 创建 GitHub Issue 或 PR
- 修改 workspace 根文件（AGENTS.md、TOOLS.md、SOUL.md、USER.md）
- 在 workspace 目录内运行 git 命令
- 提交 gep/ 运行时数据（drafts、events）到 git — 仅本地使用

允许事项：
- 读取任意文件（skills、logs、session histories、configs）
- 仅写入 `{baseDir}/gep/drafts/` 目录
- 写入 `{baseDir}/gep/events.jsonl`（仅异常周期，保留 30 条）
- 通过 `message` 工具发送消息
- `cron action=list` 和 `cron action=runs`（只读）

## 频率

由外部 cron job 配置：`0 1,9,17 * * *`（每 8 小时）。

每次执行独立选择模式 A 或模式 B，基于检测结果。
预期分布：多数为模式 B（静默），偶尔模式 A（完整报告）。
