---
name: feed-collector
version: 1.0.0
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

按优先级从以下源采集，**跳过 seen.json 中已有的 URL**：

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
pubDatetime: YYYY-MM-DDTHH:mm:ss+08:00
tags: [tag1, tag2]
featured: true/false  # score >= 8.0 时为 true
score: 8.5
sourceUrl: "https://..."
sourceType: "openai-blog"  # 见下方枚举
sourceName: "OpenAI"
---

正文内容（2-3 段摘要 + 要点）
```

sourceType 枚举：`anthropic-blog`, `openai-blog`, `deepmind-blog`, `meta-ai-blog`, `hacker-news`, `reddit`, `github-trending`, `arxiv`, `web-search`, `rss`, `jiqizhixin`, `qbitai`, `36kr`, `other`

### Step 6: 清理 seen.json

删除 `data/seen.json` 中超过 `retention_days`（默认 30 天）的条目。

### Step 7: 提交推送

```bash
cd /data/code/github.com/astralor/feed
git add -A
git commit -m "feed: YYYY-MM-DD HH:mm - N items from [sources]"
git push
```

### Step 8: Discord 推送

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

### Step 9: 构建验证（可选）

本地跑 `npm run build` 确认构建通过。Cloudflare Pages 会自动触发。

## 注意事项

- 每次采集不要花太多 token，效率优先
- web_fetch 失败时 fallback 到 web_search
- 国内源如果 web_fetch 返回空，用 web_search 代替
- 不要重复采集同一条新闻（严格依赖 seen.json）
- commit message 要简洁明了
- Discord 推送不要超过 2000 字符限制
