---
name: feed-collector
version: 1.13.0
description: "AI 信息流采集技能。定时从多个源采集 AI 领域动态，打分筛选后生成 Markdown 并推送到 Discord 和 feed.astralor.com。"
---

# Feed Collector Skill

## 概述

从多个信息源采集 AI 领域素材，AI 打分筛选后写入 `astralor/feed` 仓库，触发 Cloudflare Pages 自动构建，同时推送精选内容到 Discord。

## 仓库

- **路径**: `/data/code/github.com/astralor/feed`
- **站点**: https://feed.astralor.com
- **Discord 频道**: 📡丨ai-feed (ID: `1481477340717383721`)

## 执行流程

### Step 1: 准备

```
cd /data/code/github.com/astralor/feed
git pull --rebase
```

读取 `data/seen.json` 获取已处理 URL 列表。

### Step 2: 采集

从以下源清单采集，**跳过 seen.json 中已有的 URL**。

**⚠️ 硬规则：所有源每轮必须全部检查，不允许提前终止。** 每个源至少发起一次请求。采集阶段只管"拿到内容"，质量筛选在 Step 4 评分阶段完成。

**⏰ 时间窗口规则（必须遵守）：**
- 只采集**最近 48 小时内发布**的内容
- 判断依据：文章页面上标注的发布日期、搜索结果中的 `published` 字段
- 搜索时使用时间过滤参数（`freshness: "day"` 或 `date_after`）收窄结果
- 无法判断发布时间的内容，默认跳过
- 例外：官方博客（Anthropic/OpenAI/DeepMind/Meta）可放宽到 7 天（重要发布不容遗漏）

**📅 原文发布日期提取（必须遵守）：**
- 采集每篇文章时，**必须提取原文的发布日期**，用于 frontmatter 的 `pubDatetime`
- 提取来源（按优先级）：
  1. 文章页面中的 `<time>` 标签、`datePublished`、`article:published_time` meta
  2. `web_fetch` 返回内容中明确标注的日期（如 "Published March 15, 2026"）
  3. 搜索结果中的 `published` 字段
  4. RSS/API 返回的发布时间戳
- 如果**确实无法获取**原文日期，使用当前采集时间，但尽量避免
- 日期格式统一为 ISO 8601：`YYYY-MM-DDTHH:mm:ss+08:00`
- 如果原文只有日期没有时间，默认使用 `T12:00:00`（正午）加原文时区

**📋 源清单（全部必查，每轮逐个请求）：**

| # | 源名称 | 方法 | URL / 说明 |
|---|--------|------|-----------|
| 1 | Anthropic | `web_fetch` | `https://www.anthropic.com/research` |
| 2 | OpenAI | `web_search` | `site:openai.com/index` + 时间过滤（JS 渲染无 RSS；freshness:day 可能返回 0，补充 freshness:week） |
| 3 | DeepMind | `web_fetch` RSS | `https://deepmind.google/blog/rss.xml`（解析 `<item>` 提取标题/链接/日期） |
| 4 | Meta AI | `web_search` | `site:ai.meta.com/blog` + 时间过滤（直接 fetch 被 WAF 拦截） |
| 5 | Hacker News | `web_fetch` API | `https://hn.algolia.com/api/v1/search_by_date?query=AI+LLM+agent+model&tags=story&numericFilters=points>30&hitsPerPage=20` |
| 6 | GitHub Trending | `web_fetch` | `https://github.com/trending`（过滤 AI 相关） |
| 7 | TechCrunch AI | `web_fetch` RSS | `https://techcrunch.com/category/artificial-intelligence/feed/` |
| 8 | Wired AI | `web_fetch` RSS | `https://www.wired.com/feed/tag/ai/latest/rss`（深度报道多） |
| 9 | HuggingFace Blog | `web_fetch` RSS | `https://huggingface.co/blog/feed.xml`（开源模型/工具一手信息） |
| 10 | MIT Tech Review | `web_fetch` RSS | `https://www.technologyreview.com/feed/`（偏分析和观点） |
| 11 | Simon Willison | `web_fetch` Atom | `https://simonwillison.net/atom/everything/`（AI 工具实践者视角） |
| 12 | arXiv | `web_fetch` API | `https://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.CL+OR+cat:cs.LG&sortBy=submittedDate&max_results=20` |
| 13 | 36kr AI | `web_fetch` | `https://36kr.com/information/AI/` |
| 14 | 动态搜索 | `web_search` | 当前 AI 热点关键词（基于前面源发现的趋势补充搜索） |

**执行要求：**
- 源 1-13 为**固定源**，必须逐个请求，不论前面的源是否已找到足够内容
- 源 14（动态搜索）在固定源全部完成后执行，基于已采集内容中发现的热点趋势补充搜索
- 单个源 `web_fetch` 失败时 fallback 到 `web_search`
- 国内源 `web_fetch` 返回空时用 `web_search` 代替
- RSS/Atom 源解析 `<item>` 或 `<entry>` 提取标题、链接、发布日期，与 seen.json 比对后筛选新条目

### Step 3: 去重

对采集到的每条素材，检查 URL 是否在 `data/seen.json` 中：
- 已存在 → 跳过
- 不存在 → 加入候选列表（暂不写 seen.json，见 Step 5a）

**⚠️ Step 2-3 的输出是一个内存中的候选列表（title, url, snippet, pubDatetime, sourceType, sourceName），不是 .md 文件！**
**在 Step 4 评分 subagent 返回结果之前，禁止创建任何 .md 文件、禁止 git commit、禁止写 seen.json。**
**违反此规则会导致重复文章——这是已发生过的生产事故（ct_031）。**

### Step 4: 打分

**核心原则：评价的是"这篇文章值不值得读者花 2 分钟看"，不是"这个事件有多重要"。**

#### 三维度加权评分

**维度 1 · 信息增量（权重 35%）**
读完这篇，读者获得了多少**他不知道的东西**？
- 9-10：首次披露的技术细节/数据/方法论
- 7-8：有实质新信息，但部分已知
- 5-6：信息大部分可从其他渠道获得
- 3-4：已知信息的重新包装
- 1-2：纯复述

**维度 2 · 内容质量（权重 35%）**
**文章本身**写得怎么样？
- 9-10：深度分析 + 数据支撑 + 独到观点
- 7-8：有分析有论据，结构清晰
- 5-6：完整报道但无深度（大多数新闻稿在这里）
- 3-4：浅表/信息不完整
- 1-2：PR 软文/营销内容
- **硬规则：纯新闻稿转述（无独立分析），此维度封顶 6.0**

**维度 3 · 实用价值（权重 30%）**
对 AI 从业者/爱好者的**实际价值**
- 9-10：直接可用（开源工具、代码、可复现的方法）
- 7-8：影响认知或决策的重要信息
- 5-6：有趣但不急着知道
- 3-4：边缘相关
- 1-2：纯八卦/与实践无关

**总分计算：** `0.35 × 信息增量 + 0.35 × 内容质量 + 0.30 × 实用价值 + 减分项`

#### 内容类型校准锚点

不同类型的文章，"好"的标准不同：

| 类型 | 信息增量看什么 | 内容质量看什么 | 实用价值看什么 |
|------|------------|------------|------------|
| 技术深度文 | 有没有可复现的方法/代码 | 是否有原创分析而非转述 | 能否直接用于工作 |
| 产品/发布新闻 | 披露了多少具体参数/定价/日期 | 超越新闻稿多少（有无独立测试/对比）| 读者能否立刻使用或购买 |
| 论文解读 | 核心贡献是否清晰 | 是原文还是二手解读 | 方法是否可落地 |
| 行业评论/观点 | 有没有别人没说过的角度 | 论据是否扎实（数据 vs 臆测）| 是否改变认知 |
| 开源工具/项目 | Star 数/活跃度/解决了什么问题 | 有无文档/demo/benchmark | 能否拿来就用 |

#### 减分项（硬扣分）

**同事件重复报道（最重要的减分项）：**
- 判断依据：同一事件/产品/会议的不同角度报道
- 检查范围：本批次已采集 + seen.json 近 48h 的标题
- 第 1 篇：正常评分
- 第 2 篇：`-1.5`，scoreReason 必须注明"同事件第 2 篇，首篇为 [标题]"
- 第 3 篇起：`-3.0`
- 例外：后续文章有实质性新信息（独立测试数据、源码分析）→ 减分减半

**PR/软文：** `-1.5`
- 识别信号：只有功能列表没有技术细节；大量"革命性""颠覆性"等营销词；没有对比/局限性讨论

**标题党：** `-1.0`
- 识别信号：标题含"震惊""你不会相信""X 已死"；标题承诺与正文交付明显不符

**空洞预测：** `-1.0`
- 识别信号："20XX 年将是 AI 的关键转折点"式断言，没有数据/案例/逻辑链支撑

#### 阈值

- **≥ 6.5** → 入库
- **< 6.5** → 不收

#### Featured 判断（独立于分数）

评分完成后，对所有入库文章额外判断：**"如果读者今天只有 5 分钟，这篇是否属于'错过会遗憾'的级别？"**

**够 featured 的：**
- 行业转折点 — 新范式、新架构、重大政策（不是每个产品发布都算）
- 即时可用的高价值工具/方法 — 开源发布且质量高、马上能用
- 认知刷新 — 读完会改变你对某个问题的看法
- 独家/首发深度分析 — 不是别处都能看到的内容

**不够 featured 的：**
- 大厂例行发布（除非真的是代际跃升）
- 行业八卦/人事变动
- "第 N 个做 X 的产品"
- 有价值但不紧迫的内容（正常入库就够了）

#### 评分执行方式（必须遵守：评分由 subagent 完成）

为避免采集任务上下文混杂导致规则漂移，**本次采集的 Step 4 评分必须由专职评分 subagent 完成**。

主采集智能体职责：
- 把本批次候选条目整理成紧凑 JSON（只保留打分需要的信息）
- 读取 `data/seen.json` 的近期条目，整理出**近 48 小时已收录标题列表**（用于同事件重复减分）
- `sessions_spawn` 启动评分 subagent
- `sessions_yield` 等待评分结果回传
- 解析评分结果，决定入库/featured，并用于生成 Markdown frontmatter

评分 subagent 输入（建议 JSON 结构）：
```json
{
  "candidates": [
    {
      "id": "c1",
      "title": "...",
      "sourceUrl": "https://...",
      "sourceName": "...",
      "sourceType": "...",
      "pubDatetime": "YYYY-MM-DDTHH:mm:ss+08:00",
      "snippet": "正文关键摘录（<=600字）"
    }
  ],
  "recentTitles48h": ["...", "..."]
}
```

评分 subagent 运行要求：
- **⚠️ 反幻觉约束：subagent 必须先 `read` 本文件（SKILL.md），使用且仅使用本文件 Step 4 定义的三维度加权评分体系（信息增量 35% + 内容质量 35% + 实用价值 30%）。禁止发明任何不在本文件中的评分维度、权重、量表或规则。如果 subagent 的输出使用了本文件未定义的维度名称，主 agent 必须拒绝该结果并重新 spawn。**
- 只做评分与去重判定，不做采集、不写文件、不构建、不 git 操作
- 对 `recentTitles48h` 进行**事件聚类/同事件识别**，并按本 Step 4 的减分项执行扣分
- 对每条候选输出三维度分数、减分、总分、是否入库、是否 featured
- 输出的 `scoreBreakdown` 格式必须为：`"信息增量:N 内容质量:N 实用价值:N 减分:N"`——使用这三个中文维度名称，不得替换

评分 subagent 输出格式（必须严格，便于解析）：
- 必须输出在 `BEGIN_JSON` 与 `END_JSON` 之间
- 除 JSON 外不输出任何文本

输出 JSON schema：
```json
{
  "results": [
    {
      "id": "c1",
      "include": true,
      "score": 7.2,
      "featured": false,
      "scoreReason": "...（<=160字）",
      "scoreBreakdown": "信息增量:7 内容质量:6 实用价值:7 减分:-1.5",
      "dedup": {
        "isDuplicateEvent": true,
        "duplicateOfTitle": "...",
        "penalty": -1.5
      }
    }
  ]
}
```

主采集智能体必须将以上结构回填到文章 frontmatter：
- `score`、`featured`、`scoreReason`、`scoreBreakdown`

#### 评分输出格式（每篇必须）

```
信息增量: 7 — [理由]
内容质量: 5 — [理由]
实用价值: 6 — [理由]
减分: -1.5（同事件第 2 篇，首篇"[标题]"）
总分: 0.35×7 + 0.35×5 + 0.30×6 - 1.5 = 4.5 → 不入库
Featured: 否
```

### Step 5: 生成 Markdown

**⚠️ 前置条件检查（必须全部通过才能开始生成 .md 文件）：**
1. ✅ Step 4 评分 subagent 已返回 `BEGIN_JSON`/`END_JSON` 结果
2. ✅ 结果已解析为 JSON，每条 include=true 的候选都有 score/scoreBreakdown/scoreReason/featured
3. ✅ 当前目录下没有本轮产生的未提交 .md 文件（如果有，说明步骤顺序错误）

**只为 subagent 返回 `include=true` 的候选生成 .md 文件。** 不要为未经评分的候选生成任何文件。

### Step 5a: 更新 seen.json

在 .md 文件全部生成完成后，将**所有 Step 3 的候选 URL**（包括 include=true 和 include=false 的）写入 `data/seen.json`。这样下次采集不会重复处理被排除的低分候选。

格式：
```json
{
  "url": {
    "seen_at": "ISO-8601",
    "date": "YYYY-MM-DD"
  }
}
```

在 `src/data/blog/YYYY-MM-DD/` 目录下创建文件，文件名格式 `NNN-slug.md`（NNN 为三位数序号，如 001、012）。

**⚠️ 序号必须从已有文件的最大序号 +1 开始，不要从 001 重新编号！**
每天可能有多次采集，每次都从 001 开始会覆盖之前的文件。检查方法：
```bash
ls src/data/blog/YYYY-MM-DD/*.md 2>/dev/null | sed 's/.*\///' | sort -rn | head -1 | grep -oP '^\d+'
```
如果目录为空或不存在，从 001 开始。否则从最大值 +1 开始。

每个文件的 frontmatter 格式：
```yaml
---
title: "标题"
description: "一句话描述"
pubDatetime: YYYY-MM-DDTHH:mm:ss+08:00  # ⚠️ 必须是原文发布时间，不是采集时间
collectedAt: YYYY-MM-DDTHH:mm:ss+08:00  # 采集时间（当前时间）
category: "行业动态"  # 七选一，见下方分类规则
tags: [tag1, tag2]
featured: true/false  # 独立判断"错过会遗憾"，不由分数自动决定
score: 8.5
scoreReason: "评分依据的简短说明"
scoreBreakdown: "信息增量:8 内容质量:7 实用价值:9 减分:0"
sourceUrl: "https://..."
sourceType: "openai-blog"  # 见下方枚举
sourceName: "OpenAI"
ogImage: ""  # 原文 hero/og 图片的转存 URL（见图片处理规则）
---
```

**📂 分类规则（category 字段，单选）：**

| 分类 | 适用内容 |
|------|---------|
| `模型动态` | 新模型发布、架构创新、评测基准、模型能力对比、训练方法突破 |
| `工程实践` | 开源项目、Agent 框架、开发工具、SDK、技术教程、工程经验分享 |
| `学术前沿` | 论文解读、可解释性研究、安全对齐、训练方法、学术突破、数据集发布 |
| `行业动态` | 产品发布、融资收购、人事变动、公司战略、市场数据、裁员 |
| `深度观点` | 评论分析、趋势预判、行业反思、开发者体验、争议话题 |
| `算力硬件` | 芯片/GPU 发布、硬件设备、数据中心、推理加速、边缘计算、算力基础设施 |
| `政策伦理` | 政策监管、版权争议、AI 安全治理、社会影响研究、AI 伦理规范 |

分类判断原则：
- 同一事件不同角度可归不同类：产品发布公告 → 行业动态，技术拆解 → 工程实践
- 边界模糊时看**文章侧重点**：侧重"发生了什么" → 行业动态，侧重"怎么做" → 工程实践，侧重"为什么/意味着什么" → 深度观点
- NVIDIA GTC 硬件/芯片发布 → 算力硬件，NVIDIA GTC 软件/平台发布 → 行业动态
- MacBook/硬件性能提升 → 算力硬件
- 政策/监管/版权/伦理 → 政策伦理

**正文结构（必须包含以下部分）：**

```markdown
> **评分 8.5** · 来源：[NVIDIA Blog](https://blogs.nvidia.com/...) · 发布于 2026-03-16
>
> 评分依据：一句话说明为什么给这个分

## 要点

正文摘要内容。2-3 段，提炼核心信息和关键数据。
使用 bullet list 列出关键要点。

## 🤖 AI 点评

用 2-3 句话给出分析视角：
- 这条新闻**为什么重要**？对行业意味着什么？
- 有哪些**值得关注的信号**或后续影响？
- 与近期其他事件有什么**关联**？

点评要有观点、有洞察，不要复述摘要。语气自然，像一个懂行的人在跟你聊。
```

**⚠️ Frontmatter YAML 安全规则（必须遵守）：**
- 双引号包裹的值内部 **禁止出现裸 ASCII 双引号 `"`**，会截断 YAML 字符串
- 需要引用时使用中文引号 `「」` 或 `『』`，不要用 `""` `""` 或裸 `"`
- 冒号 `:` 后紧跟空格会被 YAML 误解析，标题/描述中避免英文冒号，用中文冒号 `：` 代替
- 生成后心里默念：*这个值放到 `yaml.parse()` 里会不会炸？*

**🖼️ 图片处理规则：**
- 只抓 **og:image**（一篇文章一张封面图）
- 获取方式：`web_fetch` 原文页面后，从 HTML 中提取 `og:image` meta tag 的 URL
- 下载到文章同目录：
  ```bash
  curl -sL -o "src/data/blog/YYYY-MM-DD/NNN-slug.jpg" "og:image URL"
  ```
- frontmatter 使用相对路径引用：`ogImage: "./NNN-slug.jpg"`
- Astro 的 `image()` schema 会自动优化（resize、WebP 转换）
- 如果 og:image 不存在或下载失败，`ogImage` 留空字符串，不阻塞流程
- **不要直接引用原站图片 URL**（防盗链 + 可能失效）
- 不抓正文插图——读者点击原文链接查看完整内容更合适

sourceType 枚举：`anthropic-blog`, `openai-blog`, `deepmind-blog`, `meta-ai-blog`, `hacker-news`, `github-trending`, `arxiv`, `techcrunch`, `wired`, `huggingface-blog`, `mit-tech-review`, `simon-willison`, `rss`, `36kr`, `web-search`, `other`

### Step 6: 清理 seen.json

删除 `data/seen.json` 中超过 `retention_days`（默认 30 天）的条目。

### Step 7: Frontmatter 校验与自动修复（必选）

在 git commit **之前**，对本次新增/修改的所有 `.md` 文件执行 YAML frontmatter 校验：

```bash
cd /data/code/github.com/astralor/feed
# 用 node 一行搞定：解析所有今天的 md 文件的 frontmatter
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
  catch(e) { errors.push({ file: f, error: e.message, line: e.mark?.line }); }
}
if (errors.length) { console.error(JSON.stringify(errors, null, 2)); process.exit(1); }
else console.log('✅ All frontmatter valid');
"
```

**必填字段检查（在 YAML 语法校验之后）：**
对本次新增的每个 `.md` 文件，确认以下字段都存在且非空：
- `title`, `description`, `pubDatetime`, `collectedAt`, `category`
- `score`, `scoreBreakdown`, `scoreReason`, `featured`
- `sourceUrl`, `sourceType`, `sourceName`

**scoreBreakdown 格式必须为：** `"信息增量:N 内容质量:N 实用价值:N 减分:N"`
如果缺失 scoreBreakdown 或格式不符：从 subagent 返回的 JSON 中重新提取。如果 subagent 未返回 scoreBreakdown，根据 score 反推各维度分并补填。

**如果 YAML 语法校验失败：**
1. 读取报错文件的 frontmatter
2. 自动修复常见问题：
   - ASCII `"` 在双引号值内部 → 替换为 `「」`
   - 英文冒号 `:` 后跟空格在值内部 → 替换为中文冒号 `：`
   - 缩进错误 → 重新对齐
3. 修复后**再次运行校验**，确认通过
4. 如果自动修复无法解决 → 删除问题文件（宁可少一条也不能炸构建）并记录日志

### Step 8: 构建验证（必选）

```bash
cd /data/code/github.com/astralor/feed
npx astro check
```

- `astro check` 必须 0 errors 才能继续
- 如果失败，回到 Step 7 排查修复
- **不通过不许 push**

### Step 9: 提交推送

```bash
cd /data/code/github.com/astralor/feed
git add -A
git commit -m "feed: YYYY-MM-DD HH:mm - N items from [sources]"
git push
```

### Step 10: Discord 推送

使用 `message` 工具发送到 📡丨ai-feed 频道（ID: `1481477340717383721`）：

```
📡 AI Feed · MM-DD HH:mm

🔥 [9.2] 标题
   → 域名 | #tag1 #tag2

📰 [7.5] 标题
   → 域名 | #tag1

共 N 条 · 完整阅读 → https://feed.astralor.com
```

- `🔥` 用于 score ≥ 8.0
- `📰` 用于 score < 8.0
- 按分数降序排列
- 推送 top 15 条，超出部分引导去网站查看

## 网站代码变更（非内容采集）

当修改 Astro 组件、布局、Schema 等网站代码时（区别于日常内容采集），push 前**必须**：

```bash
cd /data/code/github.com/astralor/feed
npm run build   # 完整流水线：astro check && astro build && pagefind
```

- **不要单独跑 `astro build`** — CF 部署命令包含 `astro check`，类型错误会导致部署失败
- `astro check` 0 errors 才能 push
- 教训（2026-03-16）：只跑了 `astro build`，漏了 `astro check`，类型错误导致 CF 部署失败

## 注意事项

- 每次采集不要花太多 token，效率优先
- web_fetch 失败时 fallback 到 web_search
- 国内源如果 web_fetch 返回空，用 web_search 代替
- 不要重复采集同一条新闻（严格依赖 seen.json）
- commit message 要简洁明了
- Discord 推送不要超过 2000 字符限制
