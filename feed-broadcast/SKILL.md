---
name: feed-broadcast
version: 1.1.0
description: "AI Feed 智能播报技能。检查新入库文章，自主判断是否值得推送，格式化后推送到指定渠道。"
---

# Feed Broadcast Skill

## 概述

检查 feed 仓库是否有新入库的文章，自主判断哪些值得推送，格式化后推送到 Cron Prompt 指定的渠道。

## 仓库

- **路径**: `/data/code/github.com/astralor/feed`

## 执行流程

### Step 1: 检查新文章

```bash
cd /data/code/github.com/astralor/feed
git pull --quiet
```

读取状态文件获取上次播报时间：
```bash
cat /root/.openclaw/workspace/state/feed-broadcast.json 2>/dev/null || echo '{"lastBroadcastAt": "1970-01-01T00:00:00Z"}'
```

查找上次播报之后的新文章：
```bash
git log --since="<lastBroadcastAt>" --name-only --pretty=format: -- 'src/data/blog/' | grep '\.md$' | sort -u
```

如果没有新文件 → 静默结束，**不发任何消息**。

### Step 2: 读取文章信息

对每个新 .md 文件，提取 frontmatter：title, description, score, featured, category, tags, sourceUrl, scoreReason。

### Step 3: 推送判断

**不是所有入库文章都值得推送。** 以下规则决定是否推：

**必推：**
- `featured: true` 的文章
- `score >= 8.0` 的文章

**选推（根据内容判断）：**
- `score 7.0-7.9`：如果话题有趣或时效性强，推；否则跳过
- `score 6.5-6.9`：默认不推，除非是非常独特的视角

**不推：**
- 纯学术论文且 score < 7.5（除非方法论有直接实用价值）
- 与最近推送过的文章高度相似的话题

### Step 4: 生成播报内容

**格式：**
```
📡 AI Feed · HH:MM

🔥 **标题**（8.5）
一句话为什么值得看 + 一句 AI 点评
<https://feed.astralor.com/posts/日期/slug/>

📰 **标题**（7.2）
一句话要点
<https://feed.astralor.com/posts/日期/slug/>

→ 全部文章：<https://feed.astralor.com>
```

**文章链接规则：**
- 从文件路径推导：`src/data/blog/<日期>/<文件名>.md` → `https://feed.astralor.com/posts/<日期>/<文件名>/`
- 用 `<>` 包裹链接以抑制预览展开

**表情规则：**
- score ≥ 8.0 → 🔥
- score 7.0-7.9 → 📰
- score < 7.0 → 📌

**语气：** 自然、有观点，像朋友推荐文章而不是新闻播报。每条用自己的话概括，不要照搬 description。

### Step 5: 发送

按 Cron Prompt 中指定的推送目标发送播报内容。

### Step 6: 更新状态

```bash
echo '{"lastBroadcastAt": "<当前 ISO 时间>"}' > /root/.openclaw/workspace/state/feed-broadcast.json
```

### Step 7: 日志

按 Cron Prompt 中指定的日志目标发送简短日志，格式：`📡 播报 HH:MM — 推送 N 条 / 跳过 M 条`

## 注意事项

- **没有新文章时不发任何消息**，不发"无新内容"
- **不是所有文章都推** — 你是推荐官，不是复读机
- 播报内容要精炼，每条 1-2 句话，不要长篇大论
- 如果只有 1 条值得推，就只推 1 条，不用凑数
