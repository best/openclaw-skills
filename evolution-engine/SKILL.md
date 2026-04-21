---
name: evolution-engine
version: 2.0.0-preview
description: "PCEC — Wiki-Native 进化引擎。以 Wiki Vault 为核心知识库，通过 Gene（策略模板）和 Capsule（验证记录）实现经验积累与复用。信号检测→经验召回→策略选择→执行→验证→固化。"
---

# Evolution Engine — PCEC

Wiki-Native 自我进化引擎。Gene 和 Capsule 存储在 Wiki Vault，所有 Session 可搜索可复用。

> 职责边界见 `references/responsibility-boundary.md`。

## 核心架构

```
Wiki Vault（本地知识库）
├── 🧬 Gene: <信号模式> — 策略模板（什么触发、怎么修、怎么验证）
│   → 所有 Session 可通过 wiki_search / memory_search 召回
│
├── 💊 Capsule: YYYY-MM-DD <目标> <摘要>
│   → 完整修复审计记录（信号/Gene/行动/结果）
│   → 可追溯、可量化、不可变
│
└── 📊 经验图谱（隐式）
    → Wiki 语义搜索 = (signal → gene → outcome) 遍历

进化周期：
Detect(多源信号) → Select(选策略) → Act(执行) → Verify(验证) → Solidify(固化到Wiki)
                    ↑                                      │
                    └──── Explore(无信号时主动突破) ←────────┘
```

## 三条规则

### 规则 1：证据链

诊断必须基于 Session Transcript 内容，禁止仅凭 duration/token/status 元数据判断。

```bash
sessions_history(sessionKey="<key>", includeTools=true)
```

### 规则 2：经验召回（信号源）

行动前搜索 Wiki 历史经验作为决策输入。**有匹配则复用，无匹配不阻塞。**

```bash
memory_search(query="<信号关键词>", corpus="all")   # 跨 Wiki + Memory
wiki_search(query="<信号描述>", corpus="wiki")       # 纯 Wiki 语义搜索
```

| 召回结果 | 怎么用 |
|---------|--------|
| 找到 Gene + 历史 outcome 好 | 优先复用其 strategy |
| 找到 Gene + 历史 outcome 差 | 标记可疑，换思路 |
| 找到 Capsule 但无 Gene | 参考 Capsule 做法，考虑提炼新 Gene |
| 无匹配 | 正常推进，Solidify 阶段写新 Gene |

### 规则 3：固化到 Wiki

实质行动后必须写回 Wiki。本地 JSONL 是运行时缓存，Wiki 才是持久知识。

| 行动类型 | 写入 Wiki |
|---------|----------|
| 修复 Skill/Cron | 新增/更新 **Capsule** + 更新关联 **Gene** |
| 发现新模式 | 新建 **Gene** 页面 |
| 知识沉淀 | `wiki_apply` synthesis 条目 |

## 数据模型（全部存储在 Wiki Vault）

### Gene — 可复用策略模板

Wiki synthesis 页面。标题格式：`Gene: <信号简述> — <策略名>`

```markdown
## 信号模式 (signals_match)
触发此 Gene 的信号特征（错误文本、指标异常、行为模式等）

## 类别 (category)
repair / optimize / innovate

## 策略 (strategy)
有序步骤列表

## 验证方法 (validation)
怎么确认修复有效

## 约束 (constraints)
max_files、forbidden_paths、风险提示

## 统计 (stats)
total_attempts / success_count / last_outcome / last_used
每次使用后更新
```

生命周期：新建 → 使用 → 升级（蒸馏）→ 废弃（连续失败）

### Capsule — 验证记录

Wiki synthesis 页面。标题格式：`Capsule: YYYY-MM-DD <目标> <动作摘要>`

```markdown
## 触发信号 (trigger_signals)

## 使用的 Gene (gene_used)
引用 Gene 标题或 "无（新模式）"

## 意图 (intent)
repair / optimize / innovate

## 行动 (action_taken)

## 影响范围 (blast_radius)
文件数 / 行数

## 结果 (outcome)
success / failed / pending_verification

## 置信度 (confidence)
0.0–1.0

## 验证状态 (verification)
已验证 / 待下次周期验证 / 验证失败
```

Capsule 不可变。修正需新建并引用原条目。

## 进化周期（5 阶段）

每天 05:00 执行一次，处理前一天完整数据。

### Phase 1: Detect — 多源信号采集

并行收集三类信号，不互相阻塞。

**1a. Cron 健康**

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

**1b. Skill 质量（增量采样）**

```bash
sessions_list(activeMinutes=1440, messageLimit=0)
# 筛选调用了 skill 工具的 session
# 每个 Skill 至少抽样最近 1 次；多次则抽样最近 3 次
```

四维评估：

| 维度 | 评估什么 | verdict |
|------|---------|---------|
| 遵循度 | 是否按 SKILL.md 流程执行？ | good/fair/poor |
| 输出质量 | 格式、内容、有无幻觉 | good/fair/poor |
| 效率 | Token/时间是否合理 | good/fair/poor |
| 模式化问题 | 同一弱点是否跨场景复现 | 有/无 |

综合判定：healthy / degrading / needs_attention / broken

**1c. Wiki 经验召回（规则 2）**

对 1a/1b 发现的每个信号，搜索 Wiki 历史经验（见规则 2 的决策矩阵）。

召回结果是 Phase 3 的**输入之一**，与其他信号并行使用。

**1d. Explore（无信号时的主动突破）**

当 1a+1b 全部正常（零异常、全 healthy），进入 Explore：

内部（每次都做）：
- 扫描 skills 仓库：过大 SKILL.md（>300行）、长期未更新（>30天）、矛盾描述
- 检查上轮遗留的待验证项

外部（低频）：
- Wiki 中长期未使用的 Gene（可能过时）
- 多个 Capsule 指向同一问题但 Gene 未更新的情况

Explore 发现进入正常流程。

### Phase 2: Select & Plan — 策略选择

基于 Phase 1 所有信号（含召回结果），制定计划。

**风险分级：**

| 级别 | 标准 | 示例 |
|------|------|------|
| **L1 自主** | 低风险：参数/Wiki/数据 | timeout 调优、Wiki 写入、drafts 清理 |
| **L2 草案** | 中高风险：Skill/Prompt/代码/Git | 编辑 SKILL.md、改 cron prompt、改脚本 |

**优先级排序（Max 3 个行动/cycle）：**
1. broken / needs_attention 的 Skill
2. Cron 异常（影响运行）
3. degrading 趋势
4. Explore 发现

### Phase 3: Act — 执行

**L1 自主执行：**

| 操作 | 方法 |
|------|------|
| 参数调优 | `cron action=update` |
| 知识沉淀 | `wiki_apply op=create_synthesis` |
| 数据维护 | gep/drafts/ 清理（过期草案归档） |
| Gene 统计更新 | 更新 Wiki Gene 页面 stats |

**L2 草案审核：**

写入 `{baseDir}/gep/drafts/YYYY-MM-DD_<名称>.json`：

```json
{
  "id": "draft_NNN",
  "created_at": "ISO-8601",
  "source": "cron-health | skill-quality | explore",
  "skill_or_job": "...",
  "evidence": { /* Phase 1 */ },
  "recall_result": { /* Phase 1c */ },
  "gene_used": "Gene标题或null",
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

### Phase 4: Verify — 验证

**即时（L1）：** 操作后立即确认生效（配置已更新/页面可搜索/文件已归档）

**延迟（L2 / 修复类）：** 下个 cycle 通过 `wiki_search` 查询上轮 Capsule 验证状态：
- L2 草案是否已被审核执行
- 上轮报告的问题是否改善（对比 Capsule outcome）
- before/after 指标

### Phase 5: Solidify — 固化到 Wiki

**5a. 写 Capsule（每次实质行动都写）**

`wiki_apply op=create_synthesis`，标题：`Capsule: YYYY-MM-DD <目标> <摘要>`

内容：触发信号 → Recall 结果 → 使用 Gene → 行动 → outcome → confidence → blast_radius → 验证计划

**5b. 更新或创建 Gene（条件性）**

| 条件 | 动作 |
|------|------|
| Recall 无匹配（新模式） | **新建** Gene |
| 复用 Gene 且成功 | 更新 stats（attempts+1, success+1） |
| 复用 Gene 但失败 | 更新 stats，标记需审查 |
| 连续 3 次成功使用同一策略 | **蒸馏**：升级 Gene（更精确的 signals_match 或更优的 strategy） |

**5c. 蒸馏（Distillation）**

全部满足才执行：
1. 同一 category ≥5 个成功 Capsule
2. 距上次蒸馏 ≥7 天
3. 当前无高优先级异常

过程：收集 Capsule → 分析共性 → 升级 Gene → 记录 `distilled_from`

## 投递

有实质内容时发送报告，全部正常则静默。

```
🔄 PCEC YYYY-MM-DD 05:00

📡 信号
  Cron: N扫 — N✓ / N⚠
  Skill: N评 — N✓ / N⚠ / N✗
  Explore: <摘要 如有>

🧠 召回
  N查 → N命中 / N未中
  复用: <Gene列表>
  新模式: <列表>

⚡ 行动
  L1: <列表>
  L2: draft_NNN → 待审核

💎 固化
  Capsule: N | Gene: 新N / 更新N
  蒸馏: <如有>
```

**静默条件：** detect 零异常 + act 零行动 + solidify 零写入 → 不发送。

## 安全边界

**禁止：**
- 无 Transcript 证据就诊断
- GitHub Issue / PR
- 修改 workspace 根文件（AGENTS.md / TOOLS.md / SOUL.md / USER.md）
- workspace 内运行 git 命令（除 Wiki 相关外）
- 只写本地 JSONL 不写 Wiki
- 提交 gep/drafts 到 git

**允许：**
- 读任意文件（skills / logs / sessions / configs / Wiki）
- L1：`wiki_apply` / `cron update` / 维护 gep/
- L2：写 `{baseDir}/gep/drafts/`
- `message` / `cron list` / `cron runs` / `sessions_list` / `sessions_history`
