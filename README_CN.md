# openclaw-skills

[English](./README.md) | 中文

OpenClaw Agent 自主开发工作流技能集。

> 本仓库由 OpenClaw Agent 通过持续的 PCEC（计划-检查-进化-提交）进化周期自维护。

## 技能列表

| 技能 | 描述 | 版本 |
|------|------|------|
| [cc-iterator](./cc-iterator/) | 自主编码代理迭代循环 | v0.1.4 |
| [chevereto-upload](./chevereto-upload/) | Chevereto V4 通用图片上传与管理 | v0.3.1 |
| [code-reviewer](./code-reviewer/) | 标准化代码审查质量门 | v0.1.1 |
| [discord-thread-archiver | 0.7.1 |
| [evolution-engine](./evolution-engine/) | PCEC v3 — 反熵自我进化引擎 | v1.3.0 |
| [feed-collect](./feed-collect/) | AI 信息流源采集与候选提取 | v1.0.0 |
| [feed-collector](./feed-collector/) | AI 信息流采集（已废弃 → feed-collect + feed-score） | v1.13.1 |
| [feed-score](./feed-score/) | AI 信息流评分、去重、Markdown 生成与发布 | v1.0.1 |
| [gemini-image-gen](./gemini-image-gen/) | Gemini 图片生成与编辑（支持多供应商降级） | v1.0.0 |
| [openclaw-usage-tracker](./openclaw-usage-tracker/) | 模型用量与费用统计（日报/范围/全量/Top Session） | v1.2.0 |
| [project-planner](./project-planner/) | Issue 优先级评估与任务规划 | v0.1.0 |
| [skill-validator](./skill-validator/) | 技能准入测试与跨平台兼容性校验 | v0.2.0 |
| [wechat-mp-publisher](./wechat-mp-publisher/) | 微信公众号 Markdown 文章发布（草稿箱） | v0.5.0 |

## 安装

在 OpenClaw 配置中添加为外部技能目录：

```jsonc
// ~/.openclaw/openclaw.json
{
  "skills": {
    "load": {
      "extraDirs": ["/path/to/openclaw-skills"]
    }
  }
}
```

## 贡献

每个技能独立一个目录，包含 `SKILL.md` 文件。编写新技能请参考 [OpenClaw 技能格式](https://docs.openclaw.ai)。

## 许可证

MIT
