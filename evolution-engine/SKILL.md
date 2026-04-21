---
name: evolution-engine
version: 5.0.0-preview
description: "PCEC v5 — Wiki-Native 进化引擎。以 Wiki Vault 为核心知识库，实现信号检测→经验召回→策略选择→执行→验证→固化的完整进化闭环。Gene（策略模板）和 Capsule（验证记录）均为 Wiki 页面，所有 Session 可搜索可复用。"
---

# Evolution Engine — PCEC v5

**Wiki-Native 自我进化引擎。** 不是观测站，不是评估者——是一个会学习、会记忆、会进化的系统。

> 职责边界见 `references/responsibility-boundary.md`。

## 核心架构：Wiki Vault = 本地 Hub

```
┌─────────────────────────────────────────────────────┐
│                   Wiki Vault                         │
│                                                     │
│  🧬 Gene: <信号模式> — 策略模板                       │
│     （什么触发、怎么修、怎么验证）                      │
│     → 所有 Session 可通过 wiki_search 召回             │
│                                                     │
│  💊 Capsule: <日期>_<目标>_<摘要>                     │
│     （一次完整修复的审计记录：信号/Gene/行动/结果）       │
│     → 可追溯、可量化、可复现                            │
│                                                     │
│  📊 Memory Graph（隐式）                               │
│     → Wiki 语义搜索 = 经验图谱遍历                      │
│     → signal → gene → outcome 映射                    │
│                                                     │
└───────────▲───────────────────────▲─────────────────┘
            │                       │
     Solidify（写回）          Recall（召回）
            │                       │
┌───────────▼───────────────────────▼─────────────────┐
│              PCEC Evolution Cycle                     │
│                                                     │
│  Detect → Recall → Select → Act → Verify → Solidify  │
│           ↑                                    │      │
│           └──────── Explore ←←←←←←←←←←←←─────┘      │
│                  （无信号时主动突破）                      │
└─────────────────────────────────────────────────────┘
```

**与历史版本的本质区别：**
- v1-v4 的"进化"是开环：发现问题 → 修 → 记日志 → **下次从头来**
- v5 是闭环：发现问题 → **查历史经验** → 选策略 → 执行 → **回写经验** → 下次更聪明

## 三条铁律

### 铁律 1：证据链（强制）

所有诊断必须基于 Session Transcript：

```bash
sessions_history(sessionKey="<key>", includeTools=true)  # Cron 异常
sessions_history(sessionKey="<key>", includeTools=true)  # Skill 调用质量
```

禁止仅凭 duration/token/status 元数据做判断。

### 铁律 2：经验优先（强制）

行动前必须先 Recall——搜索 Wiki 中是否有类似信号的历史经验：

```bash
# 优先用 memory_search（跨 Wiki + Memory）
memory_search(query="<信号关键词>", corpus="all")

# 补充用 wiki_search 做语义匹配
wiki_search(query="<信号描述>", corpus="wiki")
```

找到匹配 Gene 时：
- 历史 outcome 好 → **优先复用其策略**
- 历史 outcome 差 → **记录为 banned，换思路**
- 无匹配 → **按新问题处理，执行后写新 Gene**

**禁止在没有 Recall 的情况下直接行动。** 这是 v5 与所有历史版本的根本区别。

### 铁律 3：固化即发布（强制）

每次有实质行动（L1 执行或 L2 草案），必须向 Wiki 写入或更新资产：

| 行动类型 | 写入 Wiki 的内容 |
|---------|----------------|
| 修复了 Skill/Cron | 新增/更新 **Capsule** 页面 + 更新关联 **Gene** |
| 发现新模式 | 新建 **Gene** 页面 |
| 知识沉淀 | Wiki 条目（通过 `wiki_apply create_synthesis`） |
| 探索发现 | Wiki 条目或 Gene 候选 |

**禁止只写本地 JSONL 不写 Wiki。** 本地文件是运行时缓存，Wiki 才是持久知识。

## 数据模型（全部存储在 Wiki Vault）

### Gene — 可复用策略模板

每个 Gene 是一个 Wiki 页面（synthesis），代表一类已验证的解决策略：

```
标题格式：Gene: <信号简述> — <策略名>

内容结构：
## 信号模式 (signals_match)
  - 触发此 Gene 的信号特征（错误文本、指标异常、行为模式等）

## 类别 (category)
  - repair / optimize / innovate

## 策略 (strategy)
  - 有序步骤列表：具体怎么做

## 验证方法 (validation)
  - 怎么确认修复有效

## 约束 (constraints)
  - max_files、forbidden_paths、风险提示

## 统计 (stats)
  - total_attempts / success_count / last_outcome / last_used
  - 每次使用后更新
```

**Gene 的生命周期：**
```
新建（首次解决某类问题）→ 使用（被 Recall 匹配）→ 升级（蒸馏优化）→ 废弃（连续失败）
```

### Capsule — 验证过的修复记录

每个 Capsule 是一个 Wiki 页面，记录一次完整的进化事件：

```
标题格式：Capsule: YYYY-MM-DD <目标Skill/Cron> <动作摘要>

内容结构：
## 触发信号 (trigger_signals)
  - 检测到了什么

## 使用的 Gene (gene_used)
  - 引用的 Gene 标题（"无"表示新模式）

## 意图 (intent)
  - repair / optimize / innovate

## 行动 (action_taken)
  - 具体做了什么（改了什么文件/参数/配置）

## 影响范围 (blast_radius)
  - 文件数 / 行数

## 结果 (outcome)
  - success / failed / pending_verification

## 置信度 (confidence)
  - 0.0–1.0

## 验证状态 (verification)
  - 已验证 / 待下次周期验证 / 验证失败
```

**Capsule 不可变。** 如果需要修正，新建一条并引用原条目。

## 进化生命周期（6 阶段）

每天 05:00 执行一次。处理前一天的完整数据。

### Phase 1: Detect — 信号发现

**1a. Cron 健康（轻量扫描）**

```bash
cron action=list                                        # 全量 job
cron action=runs jobId=<id> limit=10                    # 每个 skill 类 job
```

异常阈值（触达任一即进入调查）：

| 指标 | 阈值 |
|------|------|
| 成功率（近 10 次） | <90% |
| 耗时趋势（近 5 次均值 vs 基线） | 增长 >50% |
| 连续错误 | ≥1 |
| 超时率（近 10 次） | ≥20% |

排除瞬态类：系统巡检 / 余额监控 / 报告 / 通知

**1b. Skill 质量（增量采样 — 核心价值）**

```bash
# 列出上次 PCEC 运行后新增的 session
sessions_list(activeMinutes=1440, messageLimit=0)

# 筛选调用了 skill 工具（read SKILL.md）的 session
# 每个 Skill 至少抽样最近 1 次；多次则抽样最近 3 次
```

四维评估：

| 维度 | 评估什么 |
|------|---------|
| 遵循度 | Agent 是否按 SKILL.md 流程执行？ |
| 输出质量 | 格式正确？内容充实？有无幻觉？ |
| 效率 | Token/时间是否合理？有无冗余调用？ |
| 模式化问题 | 同一弱点是否跨场景复现？ |

verdict: healthy / degrading / needs_attention / broken

**1c. Explore（无信号时的主动突破）**

当 Phase 1a + 1b 全部正常（零异常、全 healthy），进入 Explore 模式：

**内部探索（每次 explore 都做）：**
- 扫描 skills 仓库：过大的 SKILL.md（>300行）、长期未更新的 skill（>30天）、矛盾描述
- 检查 open tracker items（上轮遗留的待验证项）

**外部探索（可选，低频）：**
- 检查 Wiki 中是否有长期未被使用的 Gene（可能已过时）
- 检查是否有多个 Capsule 指向同一问题但 Gene 未更新的情况

Explore 发现的问题进入 Phase 2 正常流程。

### Phase 2: Recall — 经验召回

对 Phase 1 发现的每个信号，**必须**先搜索 Wiki 历史经验：

```bash
# 方法 1：memory_search（跨 Wiki + Memory，推荐首选）
memory_search(query="<信号关键词>", corpus="all", maxResults=5)

# 方法 2：wiki_search（纯 Wiki 语义搜索）
wiki_search(query="<信号描述>", corpus="wiki", maxResults=5)
```

**召回决策矩阵：**

| 召回结果 | 含义 | 行动 |
|---------|------|------|
| 找到 Gene + 历史 outcome 好 | 这类问题之前成功解决过 | **复用该 Gene 的 strategy** |
| 找到 Gene + 历史 outcome 差/失败 | 之前试过但没效 | **标记 Gene 为可疑，换新思路** |
| 找到 Capsule 但无 Gene | 有人修过但没提炼策略 | **参考 Capsule 的做法，考虑提炼新 Gene** |
| 什么都找不到 | 全新问题 | **作为新问题处理，Solidify 阶段写新 Gene** |

**将召回结果带入 Phase 3：** 不是从零开始规划，而是站在历史经验的肩膀上。

### Phase 3: Select & Plan — 策略选择与规划

基于 Phase 1（信号）+ Phase 2（历史经验），制定行动计划：

**3a. 风险分级**

| 级别 | 标准 | 示例 |
|------|------|------|
| **L1 自主** | 低风险，不涉及 Skill/Prompt/代码/Git | 参数调优、Wiki 知识写入、自身数据维护 |
| **L2 草案** | 中高风险，涉及 Skill 内容/Cron Prompt/代码/Git | 编辑 SKILL.md、改 cron prompt、改脚本 |

**3b. 行动方案**

对每个信号，输出：

```
信号: <是什么>
历史经验: <Recall 结果摘要>
选用策略: <复用 Gene X / 参考 Capsule Y / 全新方案>
风险等级: L1 / L2
计划: <具体做什么>
预期效果: <预测>
```

**Max 3 个行动 per cycle。** 按优先级排序：
1. broken / needs_attention 的 Skill
2. Cron 异常（影响运行的）
3. degrading 的趋势
4. Explore 发现

### Phase 4: Act — 执行

**L1 自主执行（直接做）：**

| 操作 | 方法 |
|------|------|
| 运行参数调优 | `cron action=update` |
| 知识沉淀 | `wiki_apply` op=create_synthesis |
| 自身数据维护 | gep/events.jsonl 清理/归档 |
| Gene 统计更新 | 更新 Wiki Gene 页面的 stats 段 |

**L2 草案审核（写草案）：**

写入 `{baseDir}/gep/drafts/YYYY-MM-DD_<名称>.json`：

```json
{
  "id": "draft_NNN",
  "created_at": "ISO-8601",
  "source": "cron-health | skill-quality | explore",
  "skill_or_job": "...",
  "evidence": { /* 来自 Phase 1 */ },
  "recall_result": { /* 来自 Phase 2 */ },
  "gene_used": "Gene 标题或 null",
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

### Phase 5: Verify — 验证

**5a. 即时验证（L1 操作）**

操作完成后立即检查：
- 参数修改 → 确认 job 配置已更新
- Wiki 写入 → 确认页面可搜索到
- 数据清理 → 确认文件已归档

**5a. 延迟验证（L2 草案 / 修复类操作）**

在 events.jsonl 中记录待验证项，下个 cycle 检查：
- 上轮 L2 草案是否已被审核执行
- 上轮报告的问题是否改善
- 对比 before/after 指标

### Phase 6: Solidify — 固化（最关键的新阶段）

**这是 v5 与所有历史版本的核心差异。** 每次有实质行动后，必须将经验写回 Wiki。

**6a. 写 Capsule（每次行动都写）**

通过 `wiki_apply` 创建 synthesis 页面：

```
标题: Capsule: YYYY-MM-DD <目标> <摘要>

Body:
## 触发信号
<Phase 1 检测到的信号>

## Recall 结果
<Phase 2 找到了什么历史经验>

## 使用的 Gene
<引用的 Gene 标题，或 "无（新模式）">

## 行动
<L1 执行了什么 / L2 草案提议了什么>

## 结果
outcome: success | pending_verification
confidence: 0.x
blast_radius: {files: N, lines: N}

## 验证计划
<下个 cycle 怎么验证这个 Capsule 有效>
```

**6b. 更新或创建 Gene（条件性）**

以下情况需要写/更新 Gene：

| 触发条件 | 动作 |
|---------|------|
| 全新模式（Recall 无匹配） | **新建** Gene 页面 |
| 复用了 Gene 且成功 | 更新 Gene 的 stats（attempts+1, success+1） |
| 复用了 Gene 但失败 | 更新 Gene 的 stats（attempts+1），标记需审查 |
| 连续 3 次 Capsule 成功使用同一策略 | **蒸馏**：升级 Gene 策略（更精确的 signals_match 或更优的 strategy） |

Gene 页面通过 `wiki_apply op=create_synthesis` 创建/更新。

**6c. 蒸馏（Distillation — 低频但重要）**

触发条件（全部满足才执行）：
1. 同一 category 下积累了 ≥5 个成功 Capsule
2. 距上次蒸馏 ≥7 天
3. 当前 cycle 无高优先级异常

过程：
1. 收集相关 Capsule（`wiki_search` 按 category）
2. 分析共性成功模式
3. 生成/升级 Gene：更精确的 signals_match、更精炼的 strategy
4. 在 Gene 页面记录 `distilled_from: [Capsule标题列表]`
5. 在 events.jsonl 记录蒸馏事件

## 输出规范

### events.jsonl（每次都写）

```json
{
  "id": "evt_NNN",
  "ts": "ISO-8601",
  "type": "full | quiet | explore",
  "phase_summary": {
    "detect": {"cron_scanned": N, "skills_evaluated": N, "anomalies": N},
    "recall": {"queries": N, "hits": N, "misses": N},
    "act": {"l1_actions": N, "l2_drafts": N},
    "solidify": {"capsules_written": N, "genes_created": N, "genes_updated": N}
  },
  "explore_findings": [...] | null,
  "distillation_event": {...} | null
}
```

保留最近 30 条，超出归档。

### Discord 报告（有实质内容时发送）

```
🔄 PCEC v5 进化报告 YYYY-MM-DD 05:00

📡 信号（Detect）
  Cron: N 扫描 — N 正常 / N 异常
  Skill: N 个评估 — N✓ / N⚠️ / N✗
  Explore: <发现摘要，如有>

🧠 经验召回（Recall）
  查询 N 次 → 命中 N 次 / 未命中 N 次
  复用 Gene: <列表>
  新模式: <列表>

⚡ 行动（Act）
  L1 自主: <列表>
  L2 草案: DRAFT draft_NNN → 待审核

💎 固化（Solidify）
  新增 Capsule: N 个
  新建/升级 Gene: N 个
  蒸馏: <如有>
```

全部正常 + 零行动 → **静默**（铁律 3 的噪音控制仍然生效）。

## 安全边界

**禁止：**
- 无 Transcript 证据就诊断
- 无 Recall 就行动（铁律 2）
- GitHub Issue / PR
- 修改 workspace 根文件（AGENTS.md / TOOLS.md / SOUL.md / USER.md）
- workspace 内运行 git 命令（除 Wiki 相关外）
- 只写本地 JSONL 不写 Wiki（违反铁律 3）
- 提交 gep/drafts 到 git

**允许：**
- 读任意文件（skills / logs / sessions / configs / Wiki）
- L1：`wiki_apply` / `cron update` / 维护 gep/
- L2：写 `{baseDir}/gep/drafts/`
- `message` / `cron list` / `cron runs` / `sessions_list` / `sessions_history`
