---
name: dream
description: "记忆方法论 & 整合执行——定义 T0/T1/T2/Dream 记忆职责、OpenClaw 注入预算硬约束、价值判断、遗忘机制，以及初始化/日常/深度三种执行流程。"
version: 2.5.2
---

# Dream — 记忆方法论 & 整合执行

## 0. OpenClaw 注入预算硬约束

OpenClaw 会把 workspace 根目录 `.md` 文件注入每个新会话。单文件存在硬限制：**12000 chars**。超过后会在 injected context 中被自动截断，表现类似：

`workspace bootstrap file MEMORY.md is 15164 chars (limit 12000); truncating in injected context`

这意味着：
- T0 不是“越全越好”；超过限制后会被动截断，反而丢失关键记忆。
- `MEMORY.md` 必须主动维护在硬限制以内。
- 预算按 **JS string length / chars** 理解，不按 UTF-8 bytes；检查用本 skill 的脚本。

### MEMORY.md 预算区间

| 区间 | 状态 | 动作 |
|---|---|---|
| 9000–10500 chars | 理想 | 保持，不为省 token 继续压缩 |
| 10501–11000 | 观察 | 只处理明显重复/过时/违规内容 |
| 11001–11800 | 整理 | 主动压缩低价值细节，目标回到 ≤10500 |
| 11801–12000 | 临界 | 优先整理，目标回到 ≤10500 |
| >12000 | 已影响注入 | 紧急恢复到 ≤11000，避免继续被动截断 |

### 必跑硬检查

Daily / Deep Dream 在编辑 `MEMORY.md` 前后都必须运行 bundled script：

```bash
node <skillDir>/scripts/t0-budget-check.mjs <workspaceDir> --json
```

脚本输出 `MEMORY.md` chars/bytes/lines/status，以及禁止写入内容命中行。`<skillDir>` 是本技能目录；`<workspaceDir>` 由 Cron Prompt 或用户指定。

---

## 1. 记忆架构

### T0：注入层（workspace 根目录 .md）

每次对话都可见，容量极小，必须高信噪比。

- `MEMORY.md` — 稳定事实、决策、规则、活跃项目索引、高信号教训。
- `SOUL.md` — 助手是谁、性格、长期反思。
- `USER.md` — 用户是谁、稳定偏好、背景、沟通模式。
- `TOOLS.md` — 工具选择、关键用法、环境特有注意事项。
- `AGENTS.md` — 行为规范和工作准则。

T0 只放“每次醒来都应该看到”的东西。

### T1：原始日记层

- `memory/YYYY-MM-DD*.md`
- 完整历史记录，按日期平铺。
- 默认不整理、不标记、不删除，保持原始性。
- Dream 自己的运行记录不写进 T1，写入 `dream/YYYY-MM-DD.md`。

### T2：知识库 / Vault / 历史记录

- Wiki Vault：结构化知识、操作手册、事件复盘、可复用模式。
- 外部 Vault：设备、服务、说明书、个人知识库。
- 项目仓库文档：项目自己的长期规范和状态。

T2 容量大，适合存放“知道存在即可，需要时检索”的内容。

### Dream 自身记忆

- `dream/YYYY-MM-DD.md`
- 记录 Dream 本轮做了什么、为什么、下次关注什么。
- 不写入 `MEMORY.md`，避免 T0 被维护过程污染。

---

## 2. T0 内容管理规则

### 2.1 应保留在 MEMORY.md

- 长期行为约束和安全边界。
- 用户稳定偏好和会直接影响互动方式的规则。
- 活跃项目的关键入口：仓库路径、主要工作流、必须先查哪里。
- 高复现、高代价的教训：会反复影响后续决策的坑。
- 记忆系统自身的稳定架构和维护原则。

### 2.2 应移出 MEMORY.md

| 类型 | 去哪里 | 说明 |
|---|---|---|
| 操作手册、详细步骤、长清单 | Wiki / references / 项目 docs | T0 只留检索入口和原则 |
| 事件长复盘、调查过程、证据链 | Wiki source/capsule 或 daily memory | T0 只留最终教训 |
| 项目内部详细状态 | 对应项目仓库 / devlog | T0 留项目入口和检查规则 |
| Dream 运行过程、压缩原因、备份路径 | dream diary | 禁止写入 `MEMORY.md` |
| 一次性任务结果 | daily memory | 除非形成长期规则 |
| 可实时查询的状态 | 不记或留“实时查”原则 | 模型、cron、provider、频道、版本、费用等 |

### 2.3 应直接删除（无需移出）

- 重复表达同一规则的句子。
- 已被后续结论取代的中间态描述。
- 文件维护痕迹：已压缩、旧版备份、迁移前目录、本次 review、归档路径。
- 精确动态 ID：job id、channel id、openid、运行时状态字段。
- secret 或 secret hint：API key、token 文件、password 等。

### 2.4 禁止写入 MEMORY.md

- 压缩/备份/迁移过程说明、旧版备份路径、归档文件路径。
- 具体 job id、channel id、openid。
- API key、token 文件、password、secret。
- 当前默认模型、具体 cron 模型、provider 当前状态、余额/费用实时数字。
- 一次性运行结果、临时判断、会很快过时的过程态。

---

## 3. 价值判断

面对日志中的任何信息，先判断值不值得长期化：

| 维度 | 高价值 | 低价值 |
|---|---|---|
| 复现性 | 未来类似场景会用到 | 一次性 |
| 不可替代性 | 只有记忆里能提醒 | 代码/配置/文档/命令可查 |
| 稳定性 | 长期有效 | 明天可能变化 |
| 行为影响 | 会改变助手怎么做事 | 只是背景信息 |

三高或强行为影响 → 可提取。否则留在 T1/T2。

提取后位置：
- 每次都必须看到 → T0。
- 需要时可检索 → T2。
- 只是本次 Dream 过程 → dream diary。
- 原始事实 → T1 保留原样。

---

## 4. 四动作模型

Dream 每轮都围绕四个动作：

1. **巩固 Consolidate**：近几天新信号 → T0/T2/dream diary。
2. **遗忘 Forget / Downscale**：T0 中低价值、过时、重复内容 → 移出或删除。
3. **修正 Correct**：新证据证明旧判断错了，或记录本身有误 → 原地修正，并在 dream diary 记录原因。
4. **洞察 Insight**：跨日模式、重复错误、系统性改进机会 → dream diary；必要时提炼进 T0/T2。

---

## 5. 审计规则

### 5.1 T0 预算审计（必须）

1. 运行 `t0-budget-check.mjs`。
2. 记录 `MEMORY.md` chars/lines/status。
3. 如果脚本报告 `forbiddenHits`，优先处理。
4. 如果 `MEMORY.md` >11000 chars，提出或执行整理。
5. 如果 `MEMORY.md` >12000 chars，优先恢复到 ≤11000，避免 OpenClaw 被动截断。

### 5.2 事实审计

从 `MEMORY.md` 提取可验证声明：
- 版本号、状态描述、计数、日期范围、项目状态、模型/provider/cron/频道相关描述。
- 对每条使用工具验证，不凭记忆判断。
- 动态状态尽量改写成“实时查”的规则，不写死。

### 5.3 自我声明一致性

- 读 `SOUL.md` / `USER.md` 中稳定声明。
- 对照近期日志，如果发现反复违背，写入 dream diary；形成稳定教训时再改 T0。

---

## 6. 编辑权限与安全阈值

### 可自动执行

- 修正明确错误的小范围条目。
- 删除 `MEMORY.md` 中的维护痕迹、具体动态 ID、重复句、已证伪过程态。
- 将长细节压缩为“查哪里 + 做什么”的短规则。
- 在 `MEMORY.md` >12000 chars 时，对低风险内容做紧急整理。

### 大幅调整必须通知

Cron 场景无法交互确认，因此不设置交互阻塞项；但以下情况必须在报告开头单独通知：

- 单次净删除 >20 行。
- 单次改动超过 `MEMORY.md` 15%。
- `MEMORY.md` 从 >12000 chars 恢复到限制内。
- 移出大段内容到 T2/wiki/project docs/dream diary。

通知必须说明：触发原因、改动章节、删除/移出内容类型、保留了哪些安全边界和高价值规则、before/after chars/lines、检查脚本结果。

### 禁止自动删除

即使是 Cron 自动任务，也禁止删除：
- 安全边界。
- 长期偏好。
- 活跃项目入口。
- 高信号教训。
- 不确定是否仍有行为指导价值的内容。

不确定时：保留原文，最多追加“待人工审阅”到 dream diary，不写入 `MEMORY.md`。

### 编辑后必须验证

- 再运行 `t0-budget-check.mjs`。
- `wc -l -c MEMORY.md`。
- 报告：改动章节、原因、前后 chars/lines、是否还有 `forbiddenHits`。

---

## 7. 执行流程

### 7-A：初始化（Initialization）

用于首次建立基线或用户明确要求全量整理。

1. 全量扫描 T0、memory/、wiki/vault 状态。
2. 运行 T0 budget check。
3. 按价值判断归集信号。
4. 执行四动作。
5. 写 dream diary。
6. 验证 `MEMORY.md` chars ≤11000（或说明为什么暂不能达成）。
7. 发送报告。

### 7-B：日常做梦（Daily Dream）

1. **定向**
   - 运行 T0 budget check。
   - 读 `MEMORY.md`、`SOUL.md`、`USER.md`、`TOOLS.md`、`AGENTS.md` 摘要或相关段落。
   - 读 dream/ 最近 1–2 天日记，避免重复处理。

2. **扫描近 3 天**
   - 读取最近 3 天 `memory/YYYY-MM-DD*.md`。
   - 建立事件时间线。
   - 不编辑 T1 原始日志。

3. **审计**
   - 做 T0 预算审计、事实审计、自我声明一致性审计。
   - 产出修正候选、遗忘候选、巩固候选。

4. **判断与执行**
   - 按第 3 节价值判断决定去 T0/T2/dream diary/不处理。
   - `MEMORY.md` ≤11000 时，不为省 token 做激进压缩。
   - `MEMORY.md` >11000 时，优先整理低风险内容。
   - 大幅调整自动执行，但必须按第 6 节通知。

5. **Dream 自身记忆**
   - 追加 `dream/YYYY-MM-DD.md`。
   - 记录本轮 chars、处理项、跳过项、下次关注。

6. **验证与报告**
   - 再运行 T0 budget check。
   - 发送报告，零变更也发送。

### 7-C：深度做梦（Deep Dream）

用于用户手动要求深度整理。

1. 扫描更长窗口（默认 7 天或用户指定）。
2. 可读取 session transcript 辅助补充，但 primary source 仍是 daily memory。
3. 全面审计 T0/T1/T2 一致性。
4. 处理跨日模式和系统性问题。
5. 大幅调整自动执行，但必须按第 6 节通知。
6. 写 dream diary 并报告。

---

## 8. Dream diary 格式

写入/追加 `dream/YYYY-MM-DD.md`：

```markdown
# Dream YYYY-MM-DD

mode: daily|deep|initialization
scan_window: 3d|7d|full

## Budget
- MEMORY.md: before N chars / after N chars / status
- forbiddenHits: N

## Actions
- Consolidate: ...
- Correct: ...
- Forget/Downscale: ...
- Insight: ...

## Large adjustment notice
- trigger: ...
- sections: ...
- moved/deleted types: ...
- preserved: ...

## Skipped / Needs attention
- ...

## Next attention
- ...
```

同一天多次运行追加，不覆盖。

---

## 9. 报告格式

通过 message 工具发送，投递目标由 Cron Prompt 指定：

```text
🌙 Dream (YYYY-MM-DD) [daily|deep]

🧠 MEMORY.md：before_chars → after_chars / limit 12000（status）
🔍 审计：forbiddenHits N / 动态状态 N / 事实修正 N
🔄 巩固：T0 +N / T2 +N
✏️ 修正：N 条
🗑️ 遗忘/移出：N 条
💭 洞察：...
⏭️ 下次：...
```

如果触发大幅调整，报告开头必须追加：

```text
⚠️ 大幅调整通知
- 触发原因：...
- 调整范围：...
- 删除/移出类型：...
- 保留确认：...
- 结果：before → after chars/lines，status
```

零变更也必须发送。
