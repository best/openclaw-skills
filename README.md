# openclaw-skills

English | [中文](./README_CN.md)

OpenClaw agent skills for autonomous development workflows.

> This repository is self-maintained by an OpenClaw agent through continuous PCEC (Plan-Check-Evolve-Commit) evolution cycles.

## Skills

| Skill | Description | Version |
|-------|-------------|---------|
| [cc-iterator](./cc-iterator/) | Autonomous coding agent iteration loop | v0.1.3 |
| [project-planner](./project-planner/) | Issue prioritization and task planning | v0.1.0 |
| [code-reviewer](./code-reviewer/) | Standardized code review quality gate | v0.1.0 |
| [evolution-engine](./evolution-engine/) | PCEC self-evolution engine with GEP protocol | v0.4.0 |

## Install

Clone the repo and symlink desired skills into your OpenClaw workspace:

```bash
git clone https://github.com/best/openclaw-skills.git
ln -sf /path/to/openclaw-skills/<skill-name> ~/.openclaw/workspace/skills/<skill-name>
```

## Contributing

Each skill lives in its own directory with a `SKILL.md` file. Follow the [OpenClaw skill format](https://docs.openclaw.ai) for authoring new skills.

## License

MIT
