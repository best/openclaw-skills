---
name: feed-collect
version: 2.1.0
description: "AI Feed 采集技能。从 Miniflux 本地配置 + HN API + GitHub Trending 采集 AI 领域素材，输出 candidates.json 供评分技能处理。"
---

# Feed Collect Skill

## 概述

从 Miniflux RSS 聚合器拉取增量文章，辅以 Hacker News API 和 GitHub Trending，URL 去重后写入 `data/candidates.json`，供 feed-score 技能评分。

## 仓库

- **路径**: `/data/code/github.com/astralor/feed`

## ⛔ Git 操作硬性约束

- ✅ 允许：`git add data/candidates.json data/seen.json`
- ❌ **严禁**：`git add -A`、`git add .`、`git add --all`
- ❌ **严禁**：添加 `data/` 目录以外的任何文件
- ❌ **严禁**：在 `/root/.openclaw/workspace` 目录下执行任何 git 操作
- 遇到 git 冲突时：只用 `git checkout --theirs data/` 解决，不要用 `git add -A`
- 仓库路径必须是 `/data/code/github.com/astralor/feed`，不是 workspace

## 数据源架构

```
Miniflux (26 feeds) ─── 主力，一次 API 调用拿全部增量
Hacker News API ─────── 补充，社区热点
GitHub Trending ─────── 补充，开源项目趋势
```

### Miniflux 订阅源（26 个 feed，5 个分类）

| 分类 | 源 |
|------|-----|
| AI Labs (7) | OpenAI · Google AI · Microsoft Research · Anthropic ×2 · DeepMind · Meta AI |
| Tech Media (6) | TechCrunch · The Verge · Wired · Ars Technica · VentureBeat · MIT Tech Review |
| Chinese Tech (5) | 36kr 快讯 · 36kr 科技 · AIbase · 虎嗅 · 少数派 |
| Academic (3) | arXiv cs.AI · cs.CL · cs.LG |
| Developer (5) | HuggingFace · PyTorch · GitHub Blog · Simon Willison · Lilian Weng |

## 执行流程

### Step 1: 准备

> **🚨 必读（执行前）：仓库含博客构建产物，必须忽略**
> `git status` / `git pull` 会显示数百个 `dist/`、`src/data/blog/` 的 modified/deleted 文件——这些是**博客网站构建产物**，与本采集任务**完全无关**。
> **无论看到多少 modified 文件，全部忽略，不要处理、提交、回滚任何这些文件。**
> 本技能**只操作** `data/candidates.json` 和 `data/seen.json` 两个文件，其余一律不管。

```bash
cd /data/code/github.com/astralor/feed
git pull --rebase
```

**seen.json 结构校验（必做）：**

```bash
python3 - <<'PY'
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

p = Path('data/seen.json')

if p.exists():
    data = json.loads(p.read_text('utf-8'))
else:
    data = {}

now_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
date_cst = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')

if isinstance(data, list):
    urls = [x for x in data if isinstance(x, str) and x.startswith('http')]
    uniq = list(dict.fromkeys(urls))
    data = {
        'description': 'URL/title dedup store for AI Feed collection. Schema: object with entries dict.',
        'entries': {u: {'seen_at': now_utc, 'date': date_cst, 'title': ''} for u in uniq},
    }

if data == {}:
    data = {
        'description': 'URL/title dedup store for AI Feed collection. Schema: object with entries dict.',
        'entries': {},
    }

if not isinstance(data, dict) or not isinstance(data.get('entries'), dict):
    raise SystemExit('Invalid data/seen.json schema.')

p.write_text(json.dumps(data, ensure_ascii=True, indent=2) + '\n', 'utf-8')
print('✅ seen.json schema ok; entries =', len(data['entries']))
PY
```

### Step 2: 从 Miniflux 拉取增量

先读取本地配置，再用一次 API 调用拉取所有未读文章：

```bash
python3 - <<'PY'
import json, subprocess
from pathlib import Path
cfg = json.loads(Path('/root/.openclaw/config/miniflux.json').read_text())
base_url = cfg.get('base_url', 'https://rss.astralor.com').rstrip('/')
username = cfg.get('username', 'admin')
password = cfg['password']
url = f"{base_url}/v1/entries?status=unread&order=published_at&direction=desc&limit=200"
print(subprocess.check_output(['curl', '-sf', url, '-u', f'{username}:{password}'], text=True))
PY
```

> Miniflux 凭据存放在 `/root/.openclaw/config/miniflux.json`，不要使用 OpenClaw `env.vars`。

**响应结构：**
```json
{
  "total": 100,
  "entries": [
    {
      "id": 123,
      "title": "...",
      "url": "https://...",
      "content": "HTML全文或摘要",
      "published_at": "2026-03-24T10:00:00Z",
      "feed": {
        "id": 1,
        "title": "OpenAI News",
        "category": {"title": "AI Labs"}
      }
    }
  ]
}
```

**处理逻辑：**
- 用 `exec` 调用 curl 获取 JSON，再用 Python 脚本处理
- 如果 `total > 200`，用 `offset` 参数分页拉取
- 提取每条 entry 的 `title`、`url`、`content`、`published_at`、`feed.title`、`feed.category.title`

### Step 3: 补充源采集

#### Hacker News（Algolia API）

```
web_fetch: https://hn.algolia.com/api/v1/search_by_date?query=AI+LLM+agent+model&tags=story&numericFilters=points>30&hitsPerPage=20
```

#### GitHub Trending

```
web_fetch: https://github.com/trending
```
过滤 AI/ML 相关项目（关键词匹配 description）。

- 两个补充源失败时跳过，不阻塞主流程

### Step 4: URL 去重

**URL 归一化（去重前必须执行）：**
- arXiv：统一为 `https://arxiv.org/abs/XXXX.XXXXX`（去掉 `pdf/`、`export.arxiv.org`、版本号 `vN`）
- 去除 URL 尾部的 `#` 锚点和 `?utm_*` 跟踪参数

对每条素材，用归一化后的 URL 检查 `data/seen.json` 的 `entries`：
- 已存在 → 跳过
- 不存在 → 加入候选列表

### Step 5: 输出 candidates.json

将所有新候选**追加**到 `data/candidates.json`（文件可能已有之前未处理的候选）。

```json
[
  {
    "title": "文章标题",
    "url": "https://...",
    "source": "OpenAI News",
    "sourceType": "openai-blog",
    "category": "AI Labs",
    "pubDatetime": "2026-03-24T10:00:00Z",
    "snippet": "正文关键摘录（300-600字，包含核心数据和关键信息）",
    "collectedAt": "2026-03-24T09:30:00+08:00"
  }
]
```

**snippet 生成规则：**
- Miniflux 条目的 `content` 字段已有 HTML 全文/摘要
- 用 Python 去除 HTML 标签，截取前 300-600 字符作为 snippet
- 包含具体数据、技术参数、对比信息
- HN/GitHub Trending 的 snippet 可从标题+描述生成

**sourceType 映射表：**

| feed.title 包含 | sourceType |
|----------------|------------|
| Anthropic | anthropic-blog |
| OpenAI | openai-blog |
| DeepMind | deepmind-blog |
| Meta AI | meta-ai-blog |
| Google AI / "AI" (Google) | google-ai-blog |
| Microsoft | microsoft-research |
| TechCrunch | techcrunch |
| Verge | the-verge |
| Wired | wired |
| Ars Technica | ars-technica |
| VentureBeat | venturebeat |
| MIT | mit-tech-review |
| arXiv | arxiv |
| 36氪 | 36kr |
| AIbase / AI日报 | aibase |
| 虎嗅 | huxiu |
| 少数派 | sspai |
| Hugging Face | huggingface-blog |
| PyTorch | pytorch-blog |
| GitHub Blog | github-blog |
| Simon Willison | simon-willison |
| Lil'Log / Lilian | lilian-weng |
| Hacker News | hacker-news |
| GitHub Trending | github-trending |
| 其他 | other |

**category 字段：** 直接使用 Miniflux 的 `feed.category.title`（AI Labs / Tech Media / Chinese Tech / Academic / Developer）。HN 用 `Community`，GitHub Trending 用 `Developer`。

### Step 6: 标记 Miniflux 已读

处理完成后，批量标记已处理的 entry 为已读：

```bash
python3 - <<'PY'
import json, subprocess
from pathlib import Path
cfg = json.loads(Path('/root/.openclaw/config/miniflux.json').read_text())
base_url = cfg.get('base_url', 'https://rss.astralor.com').rstrip('/')
username = cfg.get('username', 'admin')
password = cfg['password']
payload = {"entry_ids": [123, 456, 789], "status": "read"}
subprocess.check_call([
    'curl', '-sf', '-X', 'PUT', f'{base_url}/v1/entries',
    '-u', f'{username}:{password}',
    '-H', 'Content-Type: application/json',
    '-d', json.dumps(payload),
])
PY
```

### Step 7: 更新 seen.json

将新候选的 URL 和标题写入 `data/seen.json`：

```json
{
  "entries": {
    "https://...": {
      "seen_at": "2026-03-24T09:30:00Z",
      "date": "2026-03-24",
      "title": "文章标题"
    }
  }
}
```

**30 天清理（写入同一脚本中完成）：**

```python
from datetime import datetime, timezone, timedelta
cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime('%Y-%m-%d')
before = len(data['entries'])
data['entries'] = {
    u: v for u, v in data['entries'].items()
    if (v.get('date') or v.get('seen_at', '')[:10]) >= cutoff
}
print(f'🧹 seen.json cleanup: {before} → {len(data["entries"])} entries (removed {before - len(data["entries"])} older than {cutoff})')
```

**写入后结构校验：**
```bash
python3 - <<'PY'
import json
from pathlib import Path
p = Path('data/seen.json')
data = json.loads(p.read_text('utf-8'))
if not isinstance(data, dict) or not isinstance(data.get('entries'), dict):
    raise SystemExit('Invalid data/seen.json schema after write.')
bad = [k for k in data.keys() if isinstance(k, str) and k.startswith('http')]
if bad:
    raise SystemExit('Found top-level URL keys (must be under entries).')
print('✅ seen.json post-write validation ok; entries =', len(data['entries']))
PY
```

### Step 8: 提交

```bash
git add data/candidates.json data/seen.json
git commit -m "collect: YYYY-MM-DD HH:mm - N new candidates"
git push
```

如果没有新候选，跳过 commit。

## 注意事项

- **效率优先**：Miniflux 一次调用替代原来 14 次逐源爬取
- 采集阶段**不做质量判断**，质量筛选由 feed-score 负责
- candidates.json 是追加模式，不要覆盖已有内容
- **禁止**把 `data/seen.json` 写成数组或把 URL 写到 JSON 顶层
- **禁止使用 `edit` 工具**修改 feed 仓库中的任何文件，用 `exec` + Python 脚本
- Miniflux API 认证：读取 `/root/.openclaw/config/miniflux.json` 后使用 HTTP Basic Auth；不要依赖旧环境变量
- 标记已读很重要，否则下次会重复拉取
