# Feed Score 评分规则

## 去重

### URL 去重
不要用 ``data/seen.json`` 直接判定当前候选 URL 重复。采集阶段会在写入 `candidates.json` 的同时写入 `seen.json`，所以当前批次候选天然会出现在 `seen.json.entries` 中。

评分阶段的 URL 去重只比较：
- 当前批次内部重复 URL
- 已发布文章 `src/data/blog/**` frontmatter 里的 `sourceUrl`

只有命中以上两类，才把候选判为 `duplicate`。`seen.json` 只能作为采集状态/历史标题上下文，不能作为当前候选的跳过依据。

### 语义去重
获取最近 7 天已入库文章标题：
```bash
cd "$FEED_REPO"
for i in $(seq 0 6); do
  DAY=$(TZ=Asia/Shanghai date -d "$i days ago" +%Y-%m-%d)
  for f in src/data/blog/$DAY/*.md; do
    [ -f "$f" ] && head -5 "$f" | grep '^title:'
  done
done
```

候选与已有标题描述**同一事件/产品/技术**（即使措辞不同）→ 重复，verdict 设为 `"skip"`，reason 设为 `"duplicate"`。

## 三维度评分

核心原则：评价"这篇文章值不值得读者花 2 分钟看"。

| 维度 | 权重 | 评什么 |
|------|------|--------|
| 信息增量 | 35% | 读完获得多少不知道的东西 |
| 内容质量 | 35% | 文章本身写得怎么样 |
| 实用价值 | 30% | 对 AI 从业者/爱好者的实际价值 |

**总分 = 0.35 × 信息增量 + 0.35 × 内容质量 + 0.30 × 实用价值 + 减分项**

**信息增量：** 9-10 首次披露 | 7-8 有实质新信息 | 5-6 其他渠道可获得 | 3-4 重新包装

**内容质量：** 9-10 深度分析+数据 | 7-8 有分析有论据 | 5-6 完整但无深度 | **纯新闻稿转述封顶 6.0**

**实用价值：** 9-10 直接可用（开源/代码） | 7-8 影响认知决策 | 5-6 有趣但不急

### 减分项

| 类型 | 扣分 | 说明 |
|------|------|------|
| 同事件重复 | 第2篇 -1.5，第3篇起 -3.0 | 有实质新信息则减半 |
| PR/软文 | -1.5 | 只有功能列表没技术细节 |
| 标题党 | -1.0 | 标题与正文交付不符 |
| 空洞预测 | -1.0 | 无数据/案例支撑 |

### 阈值

≥ 7.0 → `"publish"` | < 7.0 → `"skip"` (reason: `"low_score"`)

## Featured 判断

对入库文章独立判断："读者今天只有 5 分钟，这篇是否'错过会遗憾'？"

够 featured：行业转折点、即时可用高价值工具、认知刷新、独家深度分析。
不够：大厂例行发布、行业八卦、"第 N 个做 X 的产品"。

## 分类

单选枚举：`模型动态` | `工程实践` | `学术前沿` | `行业动态` | `深度观点` | `算力硬件` | `政策伦理`

## sourceType 枚举

`anthropic-blog` | `openai-blog` | `deepmind-blog` | `meta-ai-blog` | `hacker-news` | `github-trending` | `arxiv` | `techcrunch` | `wired` | `huggingface-blog` | `mit-tech-review` | `simon-willison` | `rss` | `36kr` | `web-search` | `other`

## 输出 JSON Schema

将结果写入 ``data/scored-results.json``：

```json
{
  "evaluated": 14,
  "scoredAt": "2026-03-23T08:45:00+08:00",
  "results": [
    {
      "verdict": "publish",
      "url": "https://...",
      "title": "文章标题（不含双引号，用「」代替）",
      "description": "一句话描述（50-80字，不含双引号）",
      "pubDatetime": "2026-03-23T02:45:00+08:00",
      "collectedAt": "2026-03-23T02:45:00+08:00",
      "category": "工程实践",
      "tags": ["tag1", "tag2"],
      "featured": false,
      "score": 7.2,
      "scoreReason": "一句话评分依据（不含双引号）",
      "scoreBreakdown": "信息增量:7 内容质量:6 实用价值:8 减分:0",
      "sourceType": "hacker-news",
      "sourceName": "Hacker News",
      "slug": "article-slug",
      "body": "## 要点\n\n正文...\n\n## 🤖 AI 点评\n\n点评..."
    },
    {
      "verdict": "skip",
      "url": "https://...",
      "title": "...",
      "reason": "duplicate|low_score",
      "score": 5.8,
      "duplicateOf": "原文标题（仅 duplicate 时）"
    }
  ]
}
```

### 字段说明

- **slug**：URL-safe 短标识，小写英文+连字符，从标题提取关键词，15 字符以内
- **body**：Markdown 正文，必须包含 `## 要点`（2-3 段核心信息提炼）和 `## 🤖 AI 点评`（2-3 句有观点的分析）两节。基于候选 snippet 中的数据撰写，不是简单复述
- **scoreBreakdown**：格式必须为 `"信息增量:N 内容质量:N 实用价值:N 减分:N"`，减分为 0 时写 `减分:0`，不可省略任何维度
- **title/description/scoreReason**：不含双引号 `"`（用 `「」` 代替），避免破坏 YAML
- **sourceName**：从候选的 `source` 字段取人类可读名称
- **tags**：1-3 个稳定主题标签。优先复用既有主题词（如 `OpenAI`、`Anthropic`、`Claude Code`、`ChatGPT`、`Codex`、`AI Agent`、`RAG`、`LLM`、`开源`、`评测`、`推理效率`、`AI安全`），不要把分类名重复写成 tag，不要为一次性论文方法名或过细概念创建长尾 tag。
