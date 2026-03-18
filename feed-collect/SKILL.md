---
name: feed-collect
version: 1.0.0
description: "AI Feed 采集技能。从 14 个信息源采集 AI 领域素材，输出 candidates.json 供评分技能处理。"
---

# Feed Collect Skill

## 概述

从 14 个信息源采集 AI 领域新内容，URL 去重后写入 `data/candidates.json`，供 feed-score 技能评分。

## 仓库

- **路径**: `/data/code/github.com/astralor/feed`

## 执行流程

### Step 1: 准备

```bash
cd /data/code/github.com/astralor/feed
git pull --rebase
```

读取 `data/seen.json` 获取已处理 URL 列表。

### Step 2: 采集

**⚠️ 所有 14 个源必须逐个请求，不允许跳过任何一个。**

只采集**最近 48 小时内发布**的内容（官方博客可放宽到 7 天）。

| # | 源 | 方法 | URL |
|---|------|------|-----|
| 1 | Anthropic | `web_fetch` | `https://www.anthropic.com/research` |
| 2 | OpenAI | `web_search` | `site:openai.com/index`（freshness:day，无结果补 week） |
| 3 | DeepMind | `web_fetch` RSS | `https://deepmind.google/blog/rss.xml` |
| 4 | Meta AI | `web_search` | `site:ai.meta.com/blog` |
| 5 | Hacker News | `web_fetch` API | `https://hn.algolia.com/api/v1/search_by_date?query=AI+LLM+agent+model&tags=story&numericFilters=points>30&hitsPerPage=20` |
| 6 | GitHub Trending | `web_fetch` | `https://github.com/trending`（过滤 AI 相关） |
| 7 | TechCrunch AI | `web_fetch` RSS | `https://techcrunch.com/category/artificial-intelligence/feed/` |
| 8 | Wired AI | `web_fetch` RSS | `https://www.wired.com/feed/tag/ai/latest/rss` |
| 9 | HuggingFace Blog | `web_fetch` RSS | `https://huggingface.co/blog/feed.xml` |
| 10 | MIT Tech Review | `web_fetch` RSS | `https://www.technologyreview.com/feed/` |
| 11 | Simon Willison | `web_fetch` Atom | `https://simonwillison.net/atom/everything/` |
| 12 | arXiv | `web_fetch` API | `https://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.CL+OR+cat:cs.LG&sortBy=submittedDate&max_results=20` |
| 13 | 36kr AI | `web_fetch` | `https://36kr.com/information/AI/` |
| 14 | 动态搜索 | `web_search` | 基于前面源发现的热点趋势补充搜索 |

- `web_fetch` 失败时 fallback 到 `web_search`
- RSS/Atom 源解析 `<item>` 或 `<entry>` 提取标题、链接、发布日期

### Step 3: URL 去重

对每条采集到的素材，检查 URL 是否在 `data/seen.json` 的 `entries` 中：
- 已存在 → 跳过
- 不存在 → 加入候选列表

### Step 4: 输出 candidates.json

将所有新候选**追加**到 `data/candidates.json`（文件可能已有之前未处理的候选）。

```json
[
  {
    "title": "文章标题",
    "url": "https://...",
    "source": "Hacker News",
    "sourceType": "hacker-news",
    "pubDatetime": "2026-03-18T08:00:00+08:00",
    "snippet": "正文关键摘录（300-600字，包含核心数据和关键信息）",
    "collectedAt": "2026-03-18T09:30:00+08:00"
  }
]
```

**snippet 要求：** 必须包含足够信息让评分 agent 判断质量。不是一句话摘要，而是关键段落的提炼。包含具体数据、技术参数、对比信息等。

**pubDatetime 提取：** 优先从 `<time>` 标签、`datePublished` meta、RSS 时间戳提取。无法获取时用采集时间。

**sourceType 枚举：** `anthropic-blog`, `openai-blog`, `deepmind-blog`, `meta-ai-blog`, `hacker-news`, `github-trending`, `arxiv`, `techcrunch`, `wired`, `huggingface-blog`, `mit-tech-review`, `simon-willison`, `rss`, `36kr`, `web-search`, `other`

### Step 5: 更新 seen.json

将新候选的 URL 和标题写入 `data/seen.json`：

```json
{
  "entries": {
    "https://...": {
      "seen_at": "2026-03-18T09:30:00Z",
      "date": "2026-03-18",
      "title": "文章标题"
    }
  }
}
```

清理超过 30 天的旧条目。

### Step 6: 提交

```bash
git add data/candidates.json data/seen.json
git commit -m "collect: YYYY-MM-DD HH:mm - N new candidates"
git push
```

如果没有新候选，跳过 commit。

## 注意事项

- 效率优先，不要在单个源上花太多时间
- 采集阶段**不做质量判断**，只管拿到内容，质量筛选由 feed-score 负责
- candidates.json 是追加模式，不要覆盖已有内容
