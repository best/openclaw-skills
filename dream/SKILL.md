---
name: dream
description: "AI Agent 的 REM 睡眠周期——周期性记忆整合技能。扫描 daily logs 提取高价值信号，合并到分层记忆系统（T0-T3），修剪过时信息，维护索引质量，同步 Wiki Vault 结构化知识库。灵感来自 Claude Code AutoDream 和 Sleep-time Compute 论文。Use when: 定期记忆整合 cron 触发、手动请求整理记忆、记忆系统质量审查。"
version: 1.1.0
---

# Dream — 记忆整合 + Wiki 同步

> 你的使命不是"记住更多"，而是优化记忆系统的信噪比。

## 核心约束

- **300 行上限**：MEMORY.md 不超过 300 行，每条索引引用 ≤150 字符
- **不许裸删**：删除必须伴随替换（更新/降级/归档），绝不留空洞
- **绝对日期**：所有"昨天""上周""最近"必须转为 YYYY-MM-DD
- **遗忘 ≠ 删除**：过时信息降级到 Wiki Vault（结构化知识层），不是抹掉
- 每天值得长期记住的增量只有 3-5 条，多了说明没筛选

## 记忆分层（v1.1 更新）

| 层 | 位置 | 加载方式 | 成本 |
|---|------|---------|------|
| T0 注入层 | workspace 根 *.md | 每次全量注入 | 最高 |
| T1 近期层 | memory/YYYY-MM-DD.md | 今天+昨天 | 中 |
| T2 知识层 | Wiki Vault (sources/concepts/entities) | wiki_search + memory_search(extraPaths) | 低 |
| T3 归档层 | memory/archive/*.md | 极少访问 | 极低 |

> **v1.1 变更**：T2 从 `memory/reference/*.md` 迁移至 Wiki Vault（isolated 模式）。
> `memorySearch.extraPaths` 已配置指向 wiki vault 子目录，`memory_search` 可同时检索 memory/ 和 wiki/。

## 编辑规则

- edit 前必须 read 最新文件，oldText 从当前文件复制，禁止凭记忆编造
- 先做幂等性检查：内容已存在则跳过
- edit 失败：立即 read 重建 oldText/newText，仍失败则停止并报告原因
- Wiki 写入优先用 `wiki_apply`（窄变更），批量写入才考虑直接写文件后 compile

---

## 工作流：6 Phase 循环

```
Phase 1: Orient → Phase 2: Gather Signal → Phase 3: Consolidate
→ Phase 4: Prune & Wiki Migrate → Phase 5: Verify & Report
→ Phase 6: Wiki Sync & Link Migration
```

### Phase 1: Orient（定向扫描）

理解当前记忆状态，**不做任何修改**。

1. 读取上次整合时间：
```bash
cat state/heartbeat.json 2>/dev/null | jq -r '.checks.memoryMaintenance // "unknown"'
```
2. 扫描记忆目录：
```bash
wc -l MEMORY.md
ls -lt memory/*.md 2>/dev/null | head -20
```
3. 检查 Wiki 状态：
```bash
wiki_status  # 确认 vault mode=isolated, pages count
```
4. 读取所有 T0 文件：MEMORY.md、SOUL.md、USER.md、TOOLS.md
5. 记录：MEMORY.md 行数、topic 文件数、wiki 页面数、最后修改日期

### Phase 2: Gather Signal（信号采集）

从上次整合以来的 daily logs 中提取高价值信号，按类型分类标注。

**信号分类：**

| 类型 | 含义 | 优先级 |
|------|------|--------|
| 🔧 纠正 | 认知被推翻、错误被修正 | 最高 |
| ⚡ 决策 | 架构选择、工具切换、流程变更 | 高 |
| 💡 偏好 | 用户明确表达的偏好或习惯 | 高 |
| 🔄 模式 | 重复出现的行为模式、反复遇到的问题 | 中 |
| 🛠️ 系统 | 环境配置、API key、服务部署 | 中 |
| 📈 成长 | 自我反思、能力提升、性格变化 | 低但重要 |

**不提取**：通用技术知识、一次性操作细节、已在 AGENTS.md 固化的规则、临时调试过程。

每条信号标注：事实内容 + 绝对日期（从文件名推导）+ 是否与当前 T0 矛盾。

### Phase 3: Consolidate（合并整理）

将新信号合并到记忆系统，维护一致性。

**3a. MEMORY.md 整合**
- 新增量合并到对应章节，同一 topic 只保留最新状态
- **日期规范化**：`昨天/上周/最近/前几天` → `YYYY-MM-DD`
- 矛盾解决：删除旧条目并替换，加注 `（YYYY-MM-DD 更新，原：XXX）`
- 合并重叠：多条描述同一件事 → 合并为一条

**3b. SOUL.md**：检查"📈 成长"信号 → 有值得记录的 → edit

**3c. USER.md**：检查"💡 偏好"信号和关于用户的新观察 → 有 → edit

**3d. TOOLS.md**：检查"🛠️ 系统"信号 → 有新配置/工具/服务 → edit

各文件无变化则跳过，不做无意义的 edit。

### Phase 4: Prune & Wiki Migrate（修剪与知识迁移）

保持 T0 精简高效，将操作知识沉淀到 Wiki Vault。

**4a. 衰减检查** — 对 MEMORY.md 每个条目逐一审问：
- Q1: 直接影响日常行为？否 → 候选降级
- Q2: 已在 AGENTS.md 固化？是 → 删除（确认 AGENTS.md 已覆盖）
- Q3: 属于操作参考/架构知识？是 → **迁移到 Wiki Vault**（见 4d）
- Q4: 事实仍然准确？否 → 更正或替换
- Q5: 超过 300 行？→ 继续裁剪低优先级条目

**4b. 索引质量**
- 每条引用 ≤150 字符，超过的降级详情到 Wiki
- 参考索引区：使用通用说明（不再列具体文件指针）

**4c. 日志归档**
```bash
mkdir -p memory/archive
find memory/ -maxdepth 1 -name "2*.md" -mtime +14 -exec mv {} memory/archive/ \;
```
不触碰：archive/、特殊文件（openlinkos-devlog.md 等）。

**4d. Wiki 迁移（v1.1 新增）**

对判定为"需降级"的操作知识条目，按类型分流写入 Wiki：

| 条目类型 | Wiki 目标 | 示例 |
|---------|----------|---|
| 可复用模式/原则 | `concepts/<slug>` | prompt-design-principles, diagnostic-patterns |
| 具体系统/服务文档 | `entities/<slug>` | cloudreve-filelab |
| 操作手册/事件记录/清单 | `sources/<slug>` | gateway-restart, blog-writing-checklist |

迁移方式：使用 `wiki_apply(op="create_synthesis", ...)` 或直接写文件后 `openclaw wiki compile`。
**注意**：不要在单次 Dream 中批量迁移超过 10 个文件——分批进行，每次 Dream 处理最高优的几个。

### Phase 5: Verify & Report（验证与报告）

**5a. 运行验证脚本**
```bash
bash scripts/verify-dream.sh
```
脚本检查：行数 ≤300、无残留相对日期、索引引用完整性、行宽。
如有 FAIL 项，尝试修复后重跑。

**5b. Wiki 验证**
```bash
wiki_lint  # 检查矛盾、provenance 缺失、stale pages
```

**5c. 更新状态**
更新 state/heartbeat.json 中 `checks.memoryMaintenance` 时间戳。
将操作日志写入当天 daily log（memory/YYYY-MM-DD.md）。

**5d. 发送报告** — 用 message 工具发送到投递目标频道。格式：

```
🌙 Dream 整合完成 <@740564786584223845>

📊 T0 注入层
- MEMORY.md：X → Y 行（预算 300）
- SOUL.md：[变更摘要 / 无需更新]
- USER.md：[变更摘要 / 无需更新]
- TOOLS.md：[变更摘要 / 无需更新]

📝 信号（N 条）
- 🔧 纠正：...
- ⚡ 决策：...
- 💡 偏好：...
- 🔄 模式：...
- 🛠️ 系统：...

🗑️ 降级/归档
- [条目 → Wiki sources/concepts/entities 或 archive/]

📚 Wiki Vault
- 新增/更新：N 页（sources X / concepts Y / entities Z）
- 链接迁移：N 处（memory/reference/ → wiki:）

✅ 验证 X/5 通过（含 wiki_lint）
📁 归档 N 个文件

🔄 反思
[一两句本轮发现]
```

### Phase 6: Wiki Sync & Link Migration（Wiki 同步与链接迁移）

> 此 Phase 在首次运行及后续每次 Dream 时执行。首次运行包含完整的 reference → wiki 迁移和链接替换；后续运行只做增量同步。

#### 6a. Reference 批量迁移（仅首次）

如果 `memory/reference/` 目录仍存在且非空：

1. 列出所有文件：`ls memory/reference/`
2. 逐个判断归类（按 4d 的分流规则）
3. 用 `wiki_apply` 或文件写入 + compile 创建对应 wiki 页面
4. 每批最多 10 个，控制节奏
5. 全部迁移完成后报告：迁移 N/N 个文件

**文件→Wiki 映射参考表（预计算，agent 可调整）：**

| 原路径 | 目标 | 类型 |
|--------|------|---|
| prompt-design-principles.md | concepts/prompt-design | concept |
| diagnostic-patterns.md | concepts/diagnostic-patterns | concept |
| cron-best-practices.md | concepts/cron-best-practices | concept |
| remote-operation-boundaries.md | concepts/remote-ops-boundaries | concept |
| cloudreve-api.md | entities/cloudreve-filelab | entity |
| feishu-doc-permissions.md | entities/feishu-permissions | entity |
| xiaowen-agent.md | entities/xiaowen-agent | entity |
| 其余 ~33 个操作手册/事件记录/清单 | sources/<原名去扩展名> | source |

#### 6b. 链接迁移（Memory 文件中的 reference/ 指针替换）

**目标范围**：MEMORY.md + 近期 daily logs（排除 archive/ 历史快照）

1. 搜索所有 `memory/reference/` 引用：
```bash
grep -rn "memory/reference/" /root/.openclaw/workspace/MEMORY.md /root/.openclaw/workspace/memory/2026-*.md 2>/dev/null
```
2. 对每个引用，对照映射表替换为 wiki 路径格式：
   - 内文引用：`memory/reference/xxx.md` → `wiki: sources/xxx`（或 concepts/ / entities/）
   - MEMORY.md 参考索引区（L243-L284）：整块替换为通用说明（4 行）
3. 替换规则：
   - **绝对执行**：MEMORY.md 内的所有 37 处引用
   - **执行**：活跃 daily logs（2026-04-05, 04-13, 04-15）中的引用
   - **跳过**：archive/ 下的历史文件（保留原始时间戳证据）
4. 替换后 `grep -rn "memory/reference/"` 验证无残留（archive/ 除外）

#### 6c. 增量 Wiki 同步（后续每次 Dream）

如果 reference/ 已清理完毕，此步骤变为：
1. 扫描本轮 Phase 3-4 产生的新知识条目
2. 判断是否值得创建/更新 wiki 页面
3. 有则 `wiki_apply` 写入 + `wiki_lint` 验证
4. 无则报告中注明"Wiki 无变更"

#### 6d. Compiled Digest 刷新

```bash
openclaw wiki compile  # 刷新 agent-digest.json 和 claims.jsonl
```

确保下次主 session 启动时能拿到最新的 wiki digest 注入。

---

## 首次运行特殊说明

首次 v1.1.0 运行会执行完整的 reference → wiki 迁移（Phase 6a + 6b），工作量较大：
- 预计处理 ~40 个文件迁移
- 预计替换 ~42 处链接（37 MEMORY.md + 5 daily logs）
- 如果单次超时，未完成部分会在下一次 Dream 继续
- **不删除** `memory/reference/` 目录——等待手动确认后再清理
