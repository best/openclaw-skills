# openclaw-skills

OpenClaw agent skills for autonomous development workflows.

自主开发工作流的 OpenClaw Agent 技能集。

## Skills

| Skill | Description / 描述 | Version |
|-------|-------------------|---------|
| [cc-iterator](./cc-iterator/) | Autonomous coding agent iteration loop | v0.1.2 |
| [project-planner](./project-planner/) | Issue prioritization and task planning | v0.1.0 |
| [code-reviewer](./code-reviewer/) | Standardized code review quality gate | v0.1.0 |
| [evolution-engine](./evolution-engine/) | PCEC self-evolution engine | v0.1.0 |

## Install / 安装

Clone and symlink skills into your OpenClaw workspace:

```bash
git clone https://github.com/best/openclaw-skills.git
ln -sf $(pwd)/openclaw-skills/<skill-name> ~/.openclaw/workspace/skills/<skill-name>
```

Or install individual skills:

```bash
cd ~/.openclaw/workspace/skills
ln -sf /path/to/openclaw-skills/cc-iterator .
```

## License

MIT
