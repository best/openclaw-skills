---
name: evolution-engine
version: 3.0.0-preview
description: "PCEC — 受控进化引擎。以 Session Transcript 为核心证据源，对 Cron 执行健康和 Skill 调用质量做分级评估与优化。自主进化但有监管：低风险操作自主执行，高风险变更草案审核。适用于：Cron 任务诊断、Skill 质量评估与退化检测、运行参数优化、知识沉淀。"
---

# Evolution Engine — PCEC

受控的自主进化引擎。周期性评估系统质量——**不只看 Cron 有没有报错，更看 Skill 被调用时表现如何。**

> 职责边界见 `references/responsibility-boundary.md`（PCEC / Dream / Heartbeat 分工）。
>
> **与 Heartbeat 的区分**：Heartbeat 关注 Cron 运维面（存活/错误/资源），PCEC 关注 Skill 质量面（遵循度/输出质量/模式化问题）。数据来源不同，粒度不同。

## 三条铁律

### 铁律 1：证据链（强制）

所有诊断和行动必须基于 Session Transcript 内容：

1. 发现异常或评估目标 → `sessions_history(sessionKey, includeTools=true)` → 读实际发生了什么
2. 对 Cron 异常：先 `cron action=runs` 取元数据，再读 transcript 确认
3. 对 Skill 评估：直接读取调用该 Skill 的 session transcript

禁止仅凭 duration/token/status 元数据做判断。

### 铁律 2：分级授权（强制）

**Level 1 — 自主执行（低风险，直接做）：**

| 操作类型 | 示例 |
|----------|------|
| 运行参数调优 | cron job timeout 增减、加 lightContext |
| 知识沉淀 | 通过 `wiki_apply` 写入 Wiki Vault |
| 自身数据维护 | gep/events.jsonl 清理/修复 |
| 草案状态流转 | 已审核草案标记 applied/rejected |

**Level 2 — 草案审核（中高风险，写草案等批准）：**

| 操作类型 | 示例 |
|----------|------|
| 技能内容修改 | 编辑 SKILL.md |
| 执行逻辑修改 | 改 cron prompt payload |
| 代码修改 | 编辑 scripts/ |
| git 操作 | add/commit/push |

### 铁律 3：无信号静默（强制）

全部正常 → 写入轻量质量评分到 events.jsonl，不发 Discord 报告。零噪音。

## 执行流程

每天 05:00 执行一次，处理前一天的完整会话数据。

```
增量采样 → 双轨评估 → 行动(分级) → 记录
```

#### Step 1：增量采样 — 找到需要评估的 Session

**1a. Cron 健康（轻量）**

```bash
cron action=list                                      # 全量 job
cron action=runs jobId=<id>                            # 每个 skill 类 job 最近 10 次
```

异常阈值（触达任一即进入调查）：

| 指标 | 阈值 |
|------|------|
| 成功率（近 10 次） | <90% |
| 耗时趋势（近 5 次均值 vs 历史） | 增长 >50% |
| 连续错误 | ≥1 |
| 超时率（近 10 次） | ≥20% |

**排除类别**（瞬态失败不代表技能问题）：
- 系统巡检类 / 余额监控类 / 报告类 / 通知类

**1b. Skill 质量（核心）— 增量扫描**

```bash
# 列出最近 24h 内活跃的 session
sessions_list(activeMinutes=1440, messageLimit=0)

# 从中筛选出使用了 skill 工具（read SKILL.md）的 session
# 对每个被调用的 Skill，收集其调用记录
```

采样策略：
- 扫描范围：**上次 PCEC 运行之后新增的** session（增量）
- 关注点：session 中出现了 `read` 工具调用 SKILL.md 的记录
- 每个 Skill 至少抽样最近 **1 次**调用；如果 24h 内有多次调用，抽样最近 **3 次**覆盖不同场景

> **为什么是增量**：PCEC 每天 05:00 跑一次，处理前一天完整数据。不需要重复扫描已评估过的历史 session。

#### Step 2：双轨评估

**轨 A：Cron 健康（有异常时才深入）**

对 Step 1a 中标记异常的 job，读 Session Transcript：

```bash
sessions_history(sessionKey="<异常run>", limit=1, includeTools=true)
sessions_history(sessionKey="<前次成功>", limit=1)   # 对比
```

证据模式对照表：

| 症状 | Transcript 特征 |
|------|----------------|
| 模型幻觉 | 编造不存在的命令或文件 |
| Prompt 误解 | 跳过步骤或执行错误工作流 |
| API/限速 | 明确的 provider 错误信息 |
| Token 溢出 | Context 过大导致截断 |
| 逻辑循环 | 重复相同工具调用链 |
| 脚本失败 | exec 非零退出 + stderr |
| 投递失败 | message 报错但任务完成 |

置信度：high / medium / low。low → 不行动，标记"需更多数据"。

**轨 B：Skill 质量（每次都做 — 核心价值所在）**

对 Step 1b 中采样的每个 Skill 调用，读 transcript 后评估四个维度：

| 维度 | 评估什么 | 好的样子 | 坏的样子 |
|------|---------|----------|---------|
| **遵循度** | Agent 是否按 SKILL.md 流程执行？ | 逐步执行，顺序正确 | 跳步、自作主张、忽略约束 |
| **输出质量** | 结果是否符合预期？ | 格式正确、内容充实 | 空转、幻觉输出、格式错误 |
| **效率** | Token 和时间是否合理？ | 在正常范围内 | 不必要的重复调用、过度冗余 |
| **模式化问题** | 同一弱点是否跨场景复现？ | 单次偶发 | 多次调用暴露相同缺陷 |

每个 Skill 产出一份质量卡片：

```json
{
  "skill_name": "feed-score",
  "sampled_sessions": 3,
  "evaluated_at": "ISO-8601",
  "dimensions": {
    "adherence": {"score": "good/fair/poor", "notes": "..."},
    "output_quality": {"score": "good/fair/poor", "notes": "..."},
    "efficiency": {"score": "good/fair/poor", "notes": "..."},
    "pattern_issues": ["问题描述"] | null
  },
  "verdict": "healthy | degrading | needs_attention | broken",
  "confidence": "high|medium|low"
}
```

verdict 判定标准：
- **healthy**：四维度全 good 或 fair，无模式化问题
- **degrading**：有 fair + 模式化问题初现
- **needs_attention**：任一维度 poor，或有明确的功能性问题
- **broken**：多次调用 consistently poor，Skill 可能已不可用

#### Step 3：行动 — 分级决策

根据双轨评估结果，选择执行路径：

**Path A：自主执行（Level 1）**

| 触发条件 | 可执行操作 |
|----------|-----------|
| Cron timeout 反复触及上限 | 调高 timeout 参数 |
| 发现新的根因模式 | `wiki_apply` 写入知识条目 |
| events.jsonl 需要清理 | 自身数据维护 |
| 已审核草案待执行 | 标记 applied/rejected |

**Path B：草案审核（Level 2）**

| 触发条件 | 草案内容 |
|----------|---------|
| Skill verdict = needs_attention | SKILL.md 修改提案 |
| Skill verdict = broken | 紧急修复 + 回滚建议 |
| Cron 诊断发现 prompt 问题 | Cron prompt 修改提案 |
| 效率持续恶化 | 架构级优化方案 |

草案写入 `{baseDir}/gep/drafts/YYYY-MM-DD_<名称>.json`：

```json
{
  "id": "draft_NNN",
  "created_at": "ISO-8601",
  "source": "cron-health | skill-quality",
  "skill_or_job": "...",
  "evidence": { /* 来自 Step 2 */ },
  "diagnosis": "...",
  "proposed_fix": {
    "type": "skill-patch|cron-prompt-patch|config-change|new-constraint",
    "target_file": "相对路径",
    "description": "改什么、为什么",
    "risk_level": "safe|moderate|risky",
    "side_effects": "可能的副作用"
  },
  "status": "pending-review"
}
```

草案质量标准：
1. `target_file` 是具体已有文件路径
2. `description` 引用目标文件中的具体位置
3. risky = 涉及 T0 文件 / 凭证 / git / 其他 cron 配置
4. `side_effects` 至少一条
5. 一案一草

#### Step 4：记录

**4a. events.jsonl（每次都写，包括无异常时）**

```json
{
  "id": "evt_NNN",
  "ts": "ISO-8601",
  "type": "full | quiet",
  "cron_health": {"scanned": N, "healthy": N, "anomalies": N, "actions_taken": N},
  "skill_quality": {"skills_evaluated": N, "healthy": N, "degrading": N, "needs_attention": N},
  "drafts_created": N,
  "autonomous_actions": [{"what": "...", "why": "..."}]
}
```

保留最近 30 条，超出的归档到 `events-archive.jsonl`。

**4b. Discord 报告（仅在有实质内容时发送）**

有异常 or 有草案 or 有自主行动时：

```
🔄 PCEC 评估报告 YYYY-MM-DD 05:00

📊 Cron 健康：N 扫描 — N 正常 / N 异常
🔍 Cron 调查（如有异常）
  [Job] 症状/证据/诊断/置信度

🧪 Skill 质量：N 个技能评估
  [Skill] 遵循度:● 输出:● 效率:● → healthy/degrading/⚠️
  [Skill] ...

⚡ 自主执行（如有）
  [操作摘要]

📝 草案（如有）
  DRAFT draft_NNN: [摘要] → 待审核
```

全部正常 + 零草案 → **静默，不发报告**（铁律 3）。

## 安全边界

**禁止：**
- 无 transcript 证据就做诊断或动手
- GitHub Issue / PR
- 修改 workspace 根文件（AGENTS.md / TOOLS.md / SOUL.md / USER.md）
- workspace 内运行 git 命令（除 Level 1 知识沉淀外）
- 提交 gep/ drafts 到 git（drafts 仅本地）

**允许：**
- 读任意文件（skills / logs / session histories / configs）
- Level 1：`wiki_apply` 知识沉淀 / 调 cron 参数 / 维护 gep/events.jsonl
- Level 2：写 `{baseDir}/gep/drafts/`
- `message` 工具发送
- `cron action=list` / `cron action=runs`（只读）
- `sessions_list` / `sessions_history`（只读）
