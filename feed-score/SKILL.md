---
name: feed-score
version: 2.0.0
description: "AI Feed 评分与发布技能。读取 candidates.json，spawn 评分子 Agent 执行三维度评分和语义去重，用脚本批量生成 Markdown 文件，校验构建后发布到仓库。"
---

# Feed Score Skill

## 概述

编排式评分发布流程：主 Agent 负责准备和发布，子 Agent 负责评分判断，脚本负责 .md 生成。

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
  task: <见下方 Subagent Prompt>
)
```

然后调用 `sessions_yield()` 等待子 Agent 完成。

#### Subagent Prompt

```
你是 AI Feed 评分员。严格按以下步骤执行：

1. 读取评分规则：
   read /data/code/github.com/best/openclaw-skills/feed-score/references/scoring-rules.md

2. 读取候选文章：
   read /data/code/github.com/astralor/feed/data/candidates.json

3. 获取去重上下文（最近 7 天已入库文章标题）：
   exec: cd /data/code/github.com/astralor/feed && for i in $(seq 0 6); do DAY=$(TZ=Asia/Shanghai date -d "$i days ago" +%Y-%m-%d); for f in src/data/blog/$DAY/*.md; do [ -f "$f" ] && head -5 "$f" | grep '^title:'; done; done

4. 按评分规则逐篇评分所有候选。对入库文章（≥6.5 分）生成完整 body 内容（要点 + AI 点评）。

5. 将结果严格按规则中的 JSON Schema 写入：
   write /data/code/github.com/astralor/feed/data/scored-results.json

6. 输出摘要：评估 N 篇，入库 M 篇，跳过 K 篇
```

### Step 3: 处理结果

子 Agent 完成后，检查 `data/scored-results.json` 是否存在且有效。

生成 .md 文件：
```bash
cd /data/code/github.com/astralor/feed
python3 /data/code/github.com/best/openclaw-skills/feed-score/scripts/generate-posts.py data/scored-results.json
```

脚本输出 JSON 摘要（generated/skipped/errors）。generated=0 → 跳到 Step 6。

### Step 4: 构建验证

```bash
cd /data/code/github.com/astralor/feed
npm run build
```

0 errors 才继续。构建失败 → 检查生成的 .md 文件修复问题后重试。

### Step 5: 提交发布

```bash
TODAY=$(TZ=Asia/Shanghai date +%Y-%m-%d)
YESTERDAY=$(TZ=Asia/Shanghai date -d yesterday +%Y-%m-%d)

git add "src/data/blog/$TODAY" "src/data/blog/$YESTERDAY" 2>/dev/null || true

# 安全检查：不允许提交 blog 以外的文件
BAD=$(git diff --cached --name-only | grep -Ev "^src/data/blog/(${TODAY}|${YESTERDAY})/" || true)
if [ -n "$BAD" ]; then
  echo "❌ Unexpected staged files:"
  echo "$BAD"
  exit 2
fi

git commit -m "feed: $TODAY HH:MM - N items"
git push
```

### Step 6: 清理

```bash
cd /data/code/github.com/astralor/feed
echo '[]' > data/candidates.json
rm -f data/scored-results.json
git add data/candidates.json
git commit -m "score: clear processed candidates"
git push
```

## 异常处理

- **子 Agent 未生成 scored-results.json**：报错，不继续
- **generate-posts.py 报错**：检查 scored-results.json 格式是否符合 schema
- **npm run build 失败**：检查生成的 .md frontmatter（常见：YAML 特殊字符、缺失字段）
- **git push 冲突**：`git pull --rebase` 后重试

## 注意事项

- 不要发明评分规则中没有的维度
- 每篇文章必须是独立 .md 文件
- 评分逻辑全部在子 Agent 中完成，主 Agent 不做评分判断
