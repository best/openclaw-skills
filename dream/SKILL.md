---
name: dream
description: "AI Agent 的 REM 睡眠周期——周期性记忆整合技能。扫描 daily logs 提取高价值信号，合并到分层记忆系统（T0-T3），修剪过时信息，维护索引质量。灵感来自 Claude Code AutoDream 和 Sleep-time Compute 论文。Use when: 定期记忆整合 cron 触发、手动请求整理记忆、记忆系统质量审查。"
version: 1.0.0
---

# Dream — 记忆整合

> 你的使命不是"记住更多"，而是优化记忆系统的信噪比。

## 核心约束

- **300 行上限**：MEMORY.md 不超过 300 行，每条索引引用 ≤150 字符
- **不许裸删**：删除必须伴随替换（更新/降级/归档），绝不留空洞
- **绝对日期**：所有"昨天""上周""最近"必须转为 YYYY-MM-DD
- **遗忘 ≠ 删除**：过时信息降级到检索层（T2），不是抹掉
- 每天值得长期记住的增量只有 3-5 条，多了说明没筛选

## 记忆分层

| 层 | 位置 | 加载方式 | 成本 |
|---|------|---------|------|
| T0 注入层 | workspace 根 *.md | 每次全量注入 | 最高 |
| T1 近期层 | memory/YYYY-MM-DD.md | 今天+昨天 | 中 |
| T2 检索层 | memory/reference/*.md | memory_search 按需 | 低 |
| T3 归档层 | memory/archive/*.md | 极少访问 | 极低 |

## 编辑规则

- edit 前必须 read 最新文件，oldText 从当前文件复制，禁止凭记忆编造
- 先做幂等性检查：内容已存在则跳过
- edit 失败：立即 read 重建 oldText/newText，仍失败则停止并报告原因

---

## 工作流：5 Phase 循环

```
Phase 1: Orient → Phase 2: Gather Signal → Phase 3: Consolidate
→ Phase 4: Prune & Index → Phase 5: Verify & Report
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
ls memory/reference/ 2>/dev/null | head -20
```
3. 读取所有 T0 文件：MEMORY.md、SOUL.md、USER.md、TOOLS.md
4. 记录：MEMORY.md 行数、topic 文件数、最后修改日期

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
- **矛盾解决**：删除旧条目并替换，加注 `（YYYY-MM-DD 更新，原：XXX）`
- **合并重叠**：多条描述同一件事 → 合并为一条

**3b. SOUL.md**：检查"📈 成长"信号 → 有值得记录的 → edit

**3c. USER.md**：检查"💡 偏好"信号和关于用户的新观察 → 有 → edit

**3d. TOOLS.md**：检查"🛠️ 系统"信号 → 有新配置/工具/服务 → edit

各文件无变化则跳过，不做无意义的 edit。

### Phase 4: Prune & Index（修剪索引）

保持 T0 精简高效，降级过时信息。

**4a. 衰减检查** — 对 MEMORY.md 每个条目逐一审问：
- Q1: 直接影响日常行为？否 → 候选降级
- Q2: 已在 AGENTS.md 固化？是 → 删除（确认 AGENTS.md 已覆盖）
- Q3: 属于操作参考/架构知识？是 → 迁移到 memory/reference/
- Q4: 事实仍然准确？否 → 更正或替换
- Q5: 超过 300 行？→ 继续裁剪低优先级条目

**4b. 索引质量**
- 每条引用 ≤150 字符，超过的降级详情到 reference/
- 参考索引区：引用的文件必须存在，不存在的删除指针

**4c. 日志归档**
```bash
mkdir -p memory/archive memory/reference
find memory/ -maxdepth 1 -name "2*.md" -mtime +14 -exec mv {} memory/archive/ \;
```
不触碰：reference/、archive/、特殊文件（openlinkos-devlog.md 等）。

### Phase 5: Verify & Report（验证与报告）

**5a. 运行验证脚本**
```bash
bash scripts/verify-dream.sh
```
脚本检查：行数 ≤300、无残留相对日期、索引引用完整性、行宽。
如有 FAIL 项，尝试修复后重跑。

**5b. 更新状态**
更新 state/heartbeat.json 中 `checks.memoryMaintenance` 时间戳。
将操作日志写入当天 daily log（memory/YYYY-MM-DD.md）。

**5c. 发送报告** — 用 message 工具发送到投递目标频道。格式：

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
- [条目 → 去向]

✅ 验证 X/4 通过
📁 归档 N 个文件

🔄 反思
[一两句本轮发现]
```
