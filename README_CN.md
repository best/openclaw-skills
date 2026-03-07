# openclaw-skills

[English](./README.md) | 中文

OpenClaw Agent 自主开发工作流技能集。

> 本仓库由 OpenClaw Agent 通过持续的 PCEC（计划-检查-进化-提交）进化周期自维护。

## 技能列表

| 技能 | 描述 | 版本 |
|------|------|------|
| [cc-iterator](./cc-iterator/) | 自主编码代理迭代循环 | v0.1.4 |
| [project-planner](./project-planner/) | Issue 优先级评估与任务规划 | v0.1.0 |
| [code-reviewer](./code-reviewer/) | 标准化代码审查质量门 | v0.1.1 |
| [evolution-engine](./evolution-engine/) | PCEC 自我进化引擎（GEP 协议） | v0.4.0 |
| [chevereto-upload](./chevereto-upload/) | Chevereto V4 通用图片上传与管理 | v0.3.1 |
| [gemini-imagegen](./gemini-imagegen/) | Gemini 3.1 Flash Image (Nano Banana 2) 图片生成与编辑 | v0.3.4 |
| [discord-thread-archiver](./discord-thread-archiver/) | Discord Thread 智能归档（AI 对话分析） | v0.4.0 |
| [skill-validator](./skill-validator/) | 技能准入测试与跨平台兼容性校验 | v0.1.0 |

## 安装

克隆仓库，将所需技能软链接到 OpenClaw 工作区：

```bash
git clone https://github.com/best/openclaw-skills.git
ln -sf /path/to/openclaw-skills/<skill-name> ~/.openclaw/workspace/skills/<skill-name>
```

## 贡献

每个技能独立一个目录，包含 `SKILL.md` 文件。编写新技能请参考 [OpenClaw 技能格式](https://docs.openclaw.ai)。

## 许可证

MIT
