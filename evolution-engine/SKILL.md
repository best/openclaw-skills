---
name: evolution-engine
version: 2.1.0
description: "PCEC — Wiki-Native 进化引擎。以 Wiki Vault 为核心知识库，通过 Gene（策略模板）和 Capsule（验证记录）实现经验积累与复用。信号检测→经验召回→诊断→固化到Wiki。"
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
│   → 完整诊断审计记录（信号/Gene/诊断/建议）
│   → 可追溯、可量化、不可变
│
└── 📊 经验图谱（隐式）
    → Wiki 语义搜索 = (signal → gene → outcome) 遍历

进化周期：
Detect(多源信号) → Diagnose(召回+分析) → Solidify(写Wiki)
                    ↑
                    └──── Explore(无信号时主动突破)
```

**PCEC 不直接修改 Skill/Cron/代码。** 它的"进化"通过知识积累实现——写出 Gene 和 Capsule，供人类或其他系统读取后执行修复。

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

每次有实质发现或诊断，必须写回 Wiki。Wiki 是唯一持久存储。

| 行动类型 | 写入 Wiki |
|---------|----------|
| 诊断了问题 | 新增 **Capsule**（含诊断+建议） |
| 发现新模式 | 新建 **Gene** 页面 |
| 参数调优 | 新增 **Capsule** 记录变更 |
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
有序步骤列表（建议的修复方案，非强制）

## 验证方法 (validation)
怎么确认修复有效

## 统计 (stats)
total_attempts / success_count / last_outcome / last_used
每次使用后更新
```

生命周期：新建 → 使用 → 升级（蒸馏）→ 废弃（连续失败）

### Capsule — 诊断记录

Wiki synthesis 页面。标题格式：`Capsule: YYYY-MM-DD <目标> <诊断摘要>`

```markdown
## 触发信号 (trigger_signals)

## 使用的 Gene (gene_used)
引用 Gene 标题或 "无（新模式）"

## 诊断 (diagnosis)
根因分析

## 建议 (recommendation)
给人类或执行系统的具体建议（PCEC 自己不执行）

## 结果 (outcome)
observed / resolved / pending

## 置信度 (confidence)
0.0–1.0
```

Capsule 不可变。修正需新建并引用原条目。

## 进化周期（3 阶段）

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

**1d. Explore（无信号时的主动突破）**

当 1a+1b 全部正常（零异常、全 healthy），进入 Explore：

内部（每次都做）：
- 扫描 skills 仓库：过大 SKILL.md（>300行）、长期未更新（>30天）、矛盾描述
- 检查上轮 Capsule 的 pending 项是否已解决

外部（低频）：
- Wiki 中长期未使用的 Gene（可能已过时）
- 多个 Capsule 指向同一问题但 Gene 未更新的情况

Explore 发现进入正常流程。

### Phase 2: Diagnose — 召回 + 分析 + 决策

基于 Phase 1 所有信号（含召回结果），逐项分析：

**2a. Cron 异常诊断**

对标记异常的 job，读 Session Transcript 确认根因：

```bash
sessions_history(sessionKey="<异常run>", includeTools=true)
```

输出：症状 → 证据（transcript 摘要）→ 诊断 → 建议 → 置信度

**2b. Skill 质量评估汇总**

对采样的每个 Skill，输出质量卡片：

```
Skill: <name>
  遵循度: ●/○ 输出: ●/○ 效率: ●/○ 模式化问题: 有/无
  → healthy | degrading | needs_attention | broken
  建议: <具体建议>
```

**2c. 行动决策**

PCEC 可自主执行的行动：

| 行动 | 条件 | 方法 |
|------|------|------|
| Cron 参数调优 | timeout 反复触及上限等 | `cron action=update` |
| 写 Wiki（Capsule/Gene） | 每次实质诊断 | `wiki_apply` |

**Max 3 个自主行动 per cycle。** 其余作为建议写入 Capsule。

### Phase 3: Solidify — 固化到 Wiki

**3a. 写 Capsule（每次实质诊断都写）**

`wiki_apply op=create_synthesis`，标题：`Capsule: YYYY-MM-DD <目标> <摘要>`

⚠️ **关键参数格式**：`create_synthesis` 必须在**顶层**传入 `sourceIds`（字符串数组），指向实际存在的文件路径或 session key。不放 claims 内部。

```yaml
# ✅ 正确调用格式（复制此模板）
wiki_apply(
  op: "create_synthesis",
  title: "Capsule: 2026-04-21 Feed Pipeline 脚本脆弱性",
  body: "<诊断正文 markdown>",
  sourceIds:                          # ← 顶层必填数组
    - "/root/.openclaw/workspace/memory/2026-04-21.md"
    - "agent:main:cron:802b31b9-..."     # session key 也行
  claims:
    - id: "capsule-feed-fragility-0421"
      text: "Feed 管道三层脆弱性诊断"
      confidence: 0.85
      evidence:
        - sourceId: "<同上某个 sourceId>"  # evidence 引用 sourceId
          lines: "seq14-35"
          weight: 0.9
          note: "transcript 摘要"
)
```

❌ 常见错误：把 sourceId 只放在 `claims[].evidence[]` 里而漏掉顶层 `sourceIds` → 报错 `requires at least one sourceId`

内容：触发信号 → Recall 结果 → 使用 Gene → 诊断 → 建议 → confidence → 验证计划

**3b. 更新或创建 Gene（条件性）**

| 条件 | 动作 |
|------|------|
| Recall 无匹配（新模式） | **新建** Gene |
| 复用 Gene 且诊断一致 | 更新 stats（attempts+1） |
| 复用 Gene 但诊断不一致 | 更新 stats，标记需审查 |
| 连续 3 次成功使用同一策略 | **蒸馏**：升级 Gene |

**3c. 蒸馏（Distillation）**

全部满足才执行：
1. 同一 category ≥5 个成功 Capsule
2. 距上次蒸馏 ≥7 天
3. 当前无高优先级异常

过程：收集 Capsule → 分析共性 → 升级 Gene → 记录 `distilled_from`

## 投递

有实质内容时发送报告，全部正常则静默。

### 报告结构（两层：决策摘要 + 完整报告）

**第一层：决策摘要（放在最顶部，让你 3 秒内知道要不要管）**

```
⚡ 需要你介入（N 项）  ← 没有这行 = 全部自动处理，可跳过
┌───────────────────────────────────────────────
│ 🔴 <一句话概括> — 建议动作（具体到做什么）     │
│   → 可选：自己改 / 说"帮我改"我 spawn agent   │
│   → 详情：wiki_get("synthesis.capsule-...") │
└───────────────────────────────────────────────

✅ 已自动处理（N 项）  ← 纯信息，不需要你做任何事
┌───────────────────────────────────────────────
│ 🟢 <一句话结论>                               │
│ 🟢 <一句话结论>                               │
└───────────────────────────────────────────────
```

**分类规则：**

| 分类 | 标记 | 放入条件 | 示例 |
|------|------|---------|------|
| **需要介入** | 🔴 | Capsule 的 recommendation 需要人工决策或代码修改 | "Feed Pipeline 脚本脆弱性 — 需要改 generate-posts.py + 提取共享脚本" |
| **已处理** | 🟢 | 假阳性确认、参数已自动调优、纯知识沉淀 | "Cron 假阳性 — 已确认为良性" / "新 Gene 已写入 Wiki" |
| **观察中** | 🟡 | 首次发现但建议是"继续监控"，不需要立刻行动 | （一般不单独列出，归入完整报告） |

**关键原则：**
- 🔴 项必须带**具体动作**（不是模糊的"建议修复"），并给出两个出口
- 如果本轮零项需要介入，**不写「需要你介入」区块**，直接从 ✅ 开始或只写「本轮无需介入」
- 每条 🔴 控制在一行摘要 + 两行细节以内，详情放完整报告

---

**第二层：完整报告（保留原有详细格式）**

```
🔄 PCEC YYYY-MM-DD HH:MM

─── 决策摘要（如上） ───

─── 完整报告 ───

📡 信号
  Cron: N扫 — N✓ / N⚠
  Skill: N评 — N✓ / N⚠ / N✗
  Explore: <摘要 如有>

🧠 召回
  N查 → N命中 / N未中
  复用: <Gene列表>
  新模式: <列表>

🔍 诊断
  Cron异常: <诊断摘要 如有>
  Skill问题: <摘要 如有>
  自主行动: <列表 如有>

💎 固化
  Capsule: N | Gene: 新N / 更新N
  蒸馏: <如有>

📊 本轮统计
  扫描: N cron / N skill | 异常: N | 假阳性: N
  写入: N Capsule + N Gene | 召回命中率: X%
  自主行动: N 项 | 需要介入: N 项
```

**静默条件：** detect 零异常 + 零诊断 + solidify 零写入 → 不发送。

## 安全边界

**禁止：**
- 无 Transcript 证据就诊断
- 修改 SKILL.md / cron prompt / 脚本 / 代码
- GitHub Issue / PR
- 修改 workspace 根文件（AGENTS.md / TOOLS.md / SOUL.md / USER.md）
- workspace 内运行 git 命令（除 Wiki 相关外）
- 只写本地文件不写 Wiki

**允许：**
- 读任意文件（skills / logs / sessions / configs / Wiki）
- `wiki_apply` 写入 Wiki Vault
- `cron action=update` 调优运行参数
- `message` / `cron list` / `cron runs` / `sessions_list` / `sessions_history`
