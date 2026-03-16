---
name: feed-collector
version: 1.8.1
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

按优先级从以下源采集，**跳过 seen.json 中已有的 URL**。

**⏰ 时间窗口规则（必须遵守）：**
- 只采集**最近 48 小时内发布**的内容
- 判断依据：文章页面上标注的发布日期、搜索结果中的 `published` 字段
- 搜索时使用时间过滤参数（`freshness: "day"` 或 `date_after`）收窄结果
- 无法判断发布时间的内容，默认跳过
- 例外：Tier 1 官方博客可放宽到 7 天（重要发布不容遗漏）

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

**Tier 1 — 官方博客（全量，不过滤）**
- Anthropic: `web_fetch https://www.anthropic.com/research`
- OpenAI: `web_search "site:openai.com/index" + 时间过滤`（JS 渲染页面用搜索代替）
- DeepMind: `web_search "site:deepmind.google/blog" + 时间过滤`
- Meta AI: `web_fetch https://ai.meta.com/blog/`

**Tier 2 — 社区聚合（AI 打分过滤）**
- Hacker News: `web_fetch https://hacker-news.firebaseio.com/v0/topstories.json`，取 top 20 的详情，过滤 AI/ML 相关
- Reddit: `web_fetch` RSS feeds for r/MachineLearning, r/LocalLLaMA, r/artificial
- GitHub Trending: `web_fetch https://github.com/trending` 过滤 AI 相关

**Tier 3 — 学术论文（每天 1 次）**
- arXiv: `web_fetch https://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.CL+OR+cat:cs.LG&sortBy=submittedDate&max_results=20`

**Tier 4 — 国内源**
- 机器之心: `web_fetch https://www.jiqizhixin.com/`
- 量子位: `web_fetch https://www.qbitai.com/`
- 36kr AI: `web_fetch https://36kr.com/information/AI/`

**Tier 5 — 动态搜索**
- `web_search` 当前 AI 热点关键词（基于 Tier 1-3 发现的趋势）

### Step 3: 去重

对采集到的每条素材，检查 URL 是否在 `data/seen.json` 中：
- 已存在 → 跳过
- 不存在 → 继续处理，将 URL 加入 seen.json

### Step 4: 打分

对每条新素材评分（0-10），评分维度：
- **技术深度** — 是否有实质性技术内容
- **新颖性** — 是否是新信息/新观点
- **相关性** — 与 AI/LLM/Agent 领域的关联度
- **影响力** — 对行业的潜在影响

阈值：
- **≥ 8.0** → featured: true（重点关注）
- **≥ 6.0** → 入库
- **< 6.0** → 不入库

### Step 5: 生成 Markdown

在 `src/data/blog/YYYY-MM-DD/` 目录下创建文件，文件名格式 `NNN-slug.md`（NNN 为序号）。

每个文件的 frontmatter 格式：
```yaml
---
title: "标题"
description: "一句话描述"
pubDatetime: YYYY-MM-DDTHH:mm:ss+08:00  # ⚠️ 必须是原文发布时间，不是采集时间
collectedAt: YYYY-MM-DDTHH:mm:ss+08:00  # 采集时间（当前时间）
category: "行业动态"  # 七选一，见下方分类规则
tags: [tag1, tag2]
featured: true/false  # score >= 8.0 时为 true
score: 8.5
scoreReason: "评分依据的简短说明"
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

sourceType 枚举：`anthropic-blog`, `openai-blog`, `deepmind-blog`, `meta-ai-blog`, `hacker-news`, `reddit`, `github-trending`, `arxiv`, `web-search`, `rss`, `jiqizhixin`, `qbitai`, `36kr`, `other`

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

**如果校验失败：**
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
