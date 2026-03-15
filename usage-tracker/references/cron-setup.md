# Cron Setup for Daily Cost Reports

## Recommended Cron Configuration

- **Schedule**: `5 0 * * *` (Asia/Shanghai) — 每天 00:05
- **Model**: Use a cost-effective model (e.g., sonnet)
- **Session**: isolated
- **Delivery**: none (agent sends via message tool)

## Cron Prompt Template

```
执行每日费用账单推送。

1. 运行脚本：`python3 <skill_dir>/scripts/daily-cost-report.py`（不传参数，默认统计昨天）
2. 解析 JSON 输出
3. 格式化为 Discord 消息（参考 SKILL.md 中的格式模板）
4. 用 message 工具发送到目标 Discord 频道

注意：
- 如果脚本报错，发送错误信息到目标频道
- 如果某天费用为 $0 或无数据，发送一条简短说明即可
- 跳过费用为 $0 且调用次数为 0 的模型
```

## Target Channel

Configure the Discord channel ID in the cron job payload. Suggested:
- 专用 📊丨用量统计 频道（如已创建）
- 或 🔔丨通知 频道作为 fallback
