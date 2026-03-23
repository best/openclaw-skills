---
name: feed-score
version: 2.0.1
description: "AI Feed 评分与发布技能。读取 candidates.json，spawn 评分子 Agent 执行三维度评分和语义去重，用脚本批量生成 Markdown 文件，校验构建后发布到仓库。"
---

# Feed Score Skill

编排式评分发布：主 Agent 准备和发布，子 Agent 评分判断，脚本生成 .md。

## 路径

- **仓库**: `/data/code/github.com/astralor/feed`
- **技能**: `/data/code/github.com/best/openclaw-skills/feed-score`

## 执行流程

### Step 1: 准备

```bash
cd /data/code/github.com/astralor/feed
git pull --rebase
```

读取 `data/candidates.json`。为空或 `[]` → 直接结束（无候选）。

### Step 2: Spawn 评分子 Agent

```
sessions_spawn(
  runtime: "subagent",
  mode: "run",
  model: "zai/glm-5-turbo",
  task: "你是 AI Feed 评分员。读取评分规则 /data/code/github.com/best/openclaw-skills/feed-score/references/scoring-rules.md，评分 /data/code/github.com/astralor/feed/data/candidates.json 中的候选文章，结果按 schema 写入 /data/code/github.com/astralor/feed/data/scored-results.json"
)
sessions_yield()
```

### Step 3: 生成 .md

```bash
cd /data/code/github.com/astralor/feed
python3 /data/code/github.com/best/openclaw-skills/feed-score/scripts/generate-posts.py data/scored-results.json
```

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

- **子 Agent 未生成 scored-results.json** → 报错，不继续
- **generate-posts.py 报错** → 检查 scored-results.json 是否符合 references/scoring-rules.md 中的 schema
- **npm run build 失败** → 检查 .md frontmatter（常见：YAML 特殊字符）
- **git push 冲突** → `git pull --rebase` 后重试
