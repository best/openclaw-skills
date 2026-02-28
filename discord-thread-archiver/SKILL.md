---
name: discord-thread-archiver
version: 1.0.0
description: "Discord Thread 智能归档工具。根据对话内容、消息量、频道类型和 AI 判断自动归档不活跃的 Thread。"
metadata:
  openclaw:
    emoji: "📦"
    requires:
      env: ["DISCORD_BOT_TOKEN"]
allowed-tools: ["exec"]
---

# Discord Thread Archiver

Discord Thread 智能归档 Skill。分析 Thread 活跃度和对话状态，自动归档已结束的讨论。

## 能力

- **分层时间规则**：根据消息量动态调整归档阈值
- **频道差异化**：不同频道可设不同保留时长
- **结束语检测**：识别"谢谢/搞定/OK"等收尾信号
- **AI 对话判断**：用 LLM 读最后几条消息判断对话是否结束
- **保护机制**：有 pin 的 Thread 永不自动归档

## 用法

```bash
# 执行归档
python3 archiver.py

# 预览模式（不实际归档）
python3 archiver.py --dry-run

# 详细输出
python3 archiver.py --verbose

# 自定义配置
python3 archiver.py --config /path/to/config.json
```

## 配置

默认读取同目录下 `config.json`，可通过 `--config` 指定。

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| guild_id | string | 必填 | Discord 服务器 ID |
| tiers.quick | object | {max_msgs: 3, hours: 8} | 快问快答阈值 |
| tiers.normal | object | {max_msgs: 20, hours: 24} | 普通讨论阈值 |
| tiers.deep | object | {max_msgs: ∞, hours: 48} | 深度讨论阈值 |
| channel_multipliers | object | {} | 频道保留倍率 |
| ai.enabled | bool | true | 是否启用 AI 判断 |
| ai.model | string | claude-sonnet-4-6 | AI 判断使用的模型 |
| ai.provider | string | anthropic | API 类型 (anthropic) |
| ai.base_url | string | 从环境变量 | API 地址 |
| ai.api_key | string | 从环境变量 | API 密钥 |
| ai.min_inactive_hours | number | 4 | 触发 AI 判断的最小不活跃时长 |
| closing_patterns | string[] | 内置列表 | 结束语正则 |

## 环境变量

| 变量 | 说明 |
|------|------|
| DISCORD_BOT_TOKEN | Discord Bot Token（必需） |
| ARCHIVER_AI_BASE_URL | AI API 地址（可选，覆盖配置） |
| ARCHIVER_AI_API_KEY | AI API 密钥（可选，覆盖配置） |

## 决策流程

```
Thread 进入评估
  │
  ├─ 有 pin → 永不归档
  ├─ <2h 无活动 → 跳过
  ├─ 只有 bot 消息 + 4h → 归档
  │
  ├─ 最后一条有结束语 → 阈值减半
  │
  ├─ 4h+ 无活动 → AI 判断
  │   ├─ concluded → 归档
  │   ├─ ongoing → 阈值 ×1.5
  │   └─ uncertain → 走时间规则
  │
  └─ 兜底：按消息量分层时间规则
      ├─ 1-3 条 → 8h
      ├─ 4-20 条 → 24h
      └─ 20+ 条 → 48h
      （频道倍率叠加）
```

## 输出

脚本输出人类可读的日志，最后一行是 JSON 格式的结构化结果：

```json
{
  "archived": 3,
  "kept": 5,
  "failed": 0,
  "ai_calls": 4,
  "details": [
    {"name": "Thread名称", "reason": "AI: concluded (12h inactive)"}
  ]
}
```

## 注意

- 此 Skill 只负责归档逻辑，不包含调度（cron）和结果投递
- 调度和投递由主 Agent 决策配置
- Token 不要硬编码在配置文件里，走环境变量
