---
name: feed-score
version: 2.1.2
description: "AI Feed 评分与发布技能。读取 candidates.json，执行三维度评分和语义去重，用脚本批量生成 Markdown 文件，校验构建后发布到仓库。"
---

# Feed Score Skill

单 Agent 评分发布：读取评分规则 → 评分 → 脚本生成 .md → 构建验证 → 发布。

## 路径

- **仓库**: `/data/code/github.com/astralor/feed`
- **技能**: `/data/code/github.com/best/openclaw-skills/feed-score`

## ⛔ Git 操作硬性约束

- ✅ 允许：`git add src/data/blog/` `git add data/candidates.json` `git add data/scored-results.json`
- ❌ **严禁**：`git add -A`、`git add .`、`git add --all`
- ❌ **严禁**：添加 `data/` 和 `src/data/blog/` 以外的任何文件
- ❌ **严禁**：在 `/root/.openclaw/workspace` 目录下执行任何 git 操作
- 遇到 git 冲突时：只用 `git checkout --theirs data/` 解决，不要用 `git add -A`
- 仓库路径必须是 `/data/code/github.com/astralor/feed`，不是 workspace

## 执行流程

### Step 1: 准备

```bash
cd /data/code/github.com/astralor/feed
git pull --rebase
```

读取 `data/candidates.json`。为空或 `[]` → 直接结束（无候选）。

⚠️ **批量上限**：如果候选数 > 200，只取前 200 条评分，其余保留在 candidates.json 中等下次处理。将剩余候选写回 candidates.json 并 commit/push（message: `score: defer N candidates`）。这是防止大批次导致 timeout 的关键。

### Step 2: 评分

读取评分规则和去重上下文：
- `references/scoring-rules.md` — 评分维度、阈值、JSON schema
- `data/seen.json` — URL 去重
- 最近 7 天 `src/data/blog/*/` 文章标题 — 语义去重

按 scoring-rules.md 的规则评估每篇候选，将完整结果写入 `data/scored-results.json`。

`scored-results.json` 必须是顶层对象，不要写裸数组：

```json
{
  "results": [
    {
      "title": "候选标题",
      "verdict": "publish",
      "score": 7.0,
      "scoreReason": "简短评分依据",
      "scoreBreakdown": "信息增量:7 内容质量:7 实用价值:7 减分:0",
      "pubDatetime": "2026-05-04T00:00:00Z",
      "collectedAt": "2026-05-04T08:00:00+08:00"
    }
  ]
}
```

`verdict` 只能是 `publish` 或 `skip`；低于发布阈值的候选也要写入 `results` 并标记 `skip`。

### Step 3: 生成 .md

```bash
python3 /data/code/github.com/best/openclaw-skills/feed-score/scripts/generate-posts.py /data/code/github.com/astralor/feed/data/scored-results.json
```

⚠️ **必须直接调用**：`python3 <绝对路径> <参数>`，不要用 `cd ... && python3` 复合格式（v2026.4.9+ exec preflight 会拒绝）。

脚本输出 JSON 摘要。generated=0 → 跳到 Step 6。

### Step 4: 构建验证

```bash
npm run build
```

0 errors 才继续。

### Step 5: 提交发布

```bash
TODAY=$(TZ=Asia/Shanghai date +%Y-%m-%d)
YESTERDAY=$(TZ=Asia/Shanghai date -d yesterday +%Y-%m-%d)

git add "src/data/blog/$TODAY" "src/data/blog/$YESTERDAY" 2>/dev/null || true

BAD=$(git diff --cached --name-only | grep -Ev "^src/data/blog/(${TODAY}|${YESTERDAY})/" || true)
[ -n "$BAD" ] && echo "❌ Unexpected staged files: $BAD" && exit 2

git commit -m "feed: $TODAY - N items"
git push
```

### Step 6: 清理

```bash
echo '[]' > data/candidates.json
rm -f data/scored-results.json
git add data/candidates.json
git commit -m "score: clear processed candidates"
git push
```

## 异常处理

- **generate-posts.py 报错** → 检查 scored-results.json 是否符合 references/scoring-rules.md 中的 schema
- **npm run build 失败** → 检查 .md frontmatter（常见：YAML 特殊字符未转义）
- **git push 冲突** → `git pull --rebase` 后重试
