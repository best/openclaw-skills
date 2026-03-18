---
name: feed-score
version: 1.0.1
description: "AI Feed 评分与发布技能。读取 candidates.json，执行三维度评分和语义去重，生成 Markdown 文件并发布到仓库。"
---

# Feed Score Skill

## 概述

读取 `data/candidates.json` 中的候选文章，执行三维度加权评分和语义去重，生成 Markdown 文件，校验构建后提交发布。

## 仓库

- **路径**: `/data/code/github.com/astralor/feed`
- **站点**: https://feed.astralor.com

## 执行流程

### Step 1: 准备

```bash
cd /data/code/github.com/astralor/feed
git pull --rebase
```

读取 `data/candidates.json`。如果文件不存在或为空数组 `[]`，直接结束（无候选）。

### Step 2: 提取去重上下文

从 `data/seen.json` 提取近 48 小时的已收录标题列表。
从 `src/data/blog/` 今天和昨天的目录中提取已有 .md 文件的标题。
合并为 `recentTitles` 列表，用于后续语义去重。

### Step 3: 评分

**核心原则：评价的是"这篇文章值不值得读者花 2 分钟看"，不是"这个事件有多重要"。**

#### 三维度加权评分

| 维度 | 权重 | 评什么 |
|------|------|--------|
| 信息增量 | 35% | 读完获得多少不知道的东西 |
| 内容质量 | 35% | 文章本身写得怎么样 |
| 实用价值 | 30% | 对 AI 从业者/爱好者的实际价值 |

**总分 = 0.35 × 信息增量 + 0.35 × 内容质量 + 0.30 × 实用价值 + 减分项**

**各维度评分标准：**

**信息增量（35%）：**
- 9-10：首次披露的技术细节/数据/方法论
- 7-8：有实质新信息，但部分已知
- 5-6：信息大部分可从其他渠道获得
- 3-4：已知信息的重新包装

**内容质量（35%）：**
- 9-10：深度分析 + 数据支撑 + 独到观点
- 7-8：有分析有论据，结构清晰
- 5-6：完整报道但无深度
- **硬规则：纯新闻稿转述（无独立分析），封顶 6.0**

**实用价值（30%）：**
- 9-10：直接可用（开源工具、代码、可复现的方法）
- 7-8：影响认知或决策的重要信息
- 5-6：有趣但不急着知道

#### 减分项（硬扣分）

**同事件重复报道（对照 recentTitles）：**
- 判断依据：同一事件/产品/会议的不同角度报道
- 第 2 篇：`-1.5`，scoreReason 注明"同事件第 2 篇，首篇为 [标题]"
- 第 3 篇起：`-3.0`
- 例外：后续文章有实质性新信息 → 减分减半

**PR/软文：** `-1.5`（只有功能列表没技术细节，大量营销词）
**标题党：** `-1.0`（标题承诺与正文交付明显不符）
**空洞预测：** `-1.0`（无数据/案例支撑的断言）

#### 阈值

- **≥ 6.5** → 入库
- **< 6.5** → 不入库

#### Featured 判断（独立于分数）

对所有入库文章额外判断：**"如果读者今天只有 5 分钟，这篇是否属于'错过会遗憾'的级别？"**

**够 featured：** 行业转折点、即时可用的高价值工具、认知刷新、独家深度分析
**不够 featured：** 大厂例行发布、行业八卦、"第 N 个做 X 的产品"

### Step 4: 生成 Markdown

确定序号：
```bash
ls src/data/blog/YYYY-MM-DD/*.md 2>/dev/null | sed 's/.*\///' | sort -rn | head -1 | grep -oP '^\d+'
```
从最大值 +1 开始。目录不存在则从 001。

文件路径：`src/data/blog/YYYY-MM-DD/NNN-slug.md`

**Frontmatter 模板：**
```yaml
---
title: "标题"
description: "一句话描述"
pubDatetime: YYYY-MM-DDTHH:mm:ss+08:00
collectedAt: YYYY-MM-DDTHH:mm:ss+08:00
category: "行业动态"
tags: [tag1, tag2]
featured: true/false
score: 7.2
scoreReason: "评分依据"
scoreBreakdown: "信息增量:7 内容质量:6 实用价值:8 减分:-1.5"
sourceUrl: "https://..."
sourceType: "hacker-news"
sourceName: "Hacker News"
ogImage: ""
---
```

**分类（category，单选）：** `模型动态` | `工程实践` | `学术前沿` | `行业动态` | `深度观点` | `算力硬件` | `政策伦理`

**正文结构：**
```markdown
> **评分 7.2** · 来源：[Source](url) · 发布于 YYYY-MM-DD
>
> 评分依据：一句话

## 要点

2-3 段核心信息提炼。

## 🤖 AI 点评

2-3 句分析视角，有观点有洞察，不复述摘要。
```

**图片处理：** 从原文提取 og:image，下载到文章同目录，frontmatter 用相对路径 `./NNN-slug.jpg`。失败则 ogImage 留空。

**YAML 安全规则：** 值内禁止裸 `"`（用「」代替），避免英文冒号后紧跟空格（用中文冒号 `：`）。

### Step 5: 校验

```bash
node -e "
const fs = require('fs');
const yaml = require('./node_modules/js-yaml');
const glob = require('fs').readdirSync('src/data/blog').flatMap(d =>
  fs.readdirSync('src/data/blog/'+d).filter(f=>f.endsWith('.md')).map(f=>'src/data/blog/'+d+'/'+f)
);
let errors = [];
for (const f of glob) {
  const content = fs.readFileSync(f, 'utf8');
  const m = content.match(/^---\n([\s\S]*?)\n---/);
  if (!m) continue;
  try { yaml.load(m[1]); }
  catch(e) { errors.push({ file: f, error: e.message }); }
}
if (errors.length) { console.error(JSON.stringify(errors, null, 2)); process.exit(1); }
else console.log('✅ All frontmatter valid');
"
```

YAML 失败则修复（`"` → `「」`，`: ` → `：`）或删除问题文件。

### Step 6: 构建验证

```bash
npm run build
```

必须 0 errors 才能继续。失败则回到 Step 5 排查。

### Step 7: 提交发布

```bash
git add -A
git commit -m "feed: YYYY-MM-DD HH:mm - N items from [sources]"
git push
```

### Step 8: 清空 candidates

将 `data/candidates.json` 重置为空数组 `[]`，commit + push：
```bash
echo '[]' > data/candidates.json
git add data/candidates.json
git commit -m "score: clear processed candidates"
git push
```

## 注意事项

- scoreBreakdown 格式必须为 `"信息增量:N 内容质量:N 实用价值:N 减分:N"`，减分为 0 时写 `减分:0`，不可省略
- 不要发明任何不在本文件中的评分维度
- 每篇文章必须是独立 .md 文件，禁止聚合
- 如果 candidates.json 为空或不存在，直接结束，不报错
