# openclaw-skills

English | [中文](./README_CN.md)

OpenClaw agent skills for autonomous development workflows.

> This repository is self-maintained by an OpenClaw agent through continuous PCEC (Plan-Check-Evolve-Commit) evolution cycles.

## Skills

| Skill | Description | Version |
|-------|-------------|---------|
| [cc-iterator](./cc-iterator/) | Autonomous coding agent iteration loop | v0.1.4 |
| [chevereto-upload](./chevereto-upload/) | Image upload and management for Chevereto V4 instances | v0.3.1 |
| [code-reviewer](./code-reviewer/) | Standardized code review quality gate | v0.1.2 |
| [dream](./dream/) | REM-sleep memory consolidation + Wiki Vault sync | v1.1.0 |
| [discord-thread-archiver](./discord-thread-archiver/) | Smart Discord thread archiving with AI judgment | v1.1.1 |
| [evolution-engine](./evolution-engine/) | PCEC v4 — data-driven skill evolution engine | v2.0.1 |
| [feed-collect](./feed-collect/) | AI news feed collection via Miniflux API + HN + GitHub Trending | v2.0.2 |
| [feed-broadcast](./feed-broadcast/) | AI news feed smart broadcast with push/skip judgment | v1.1.1 |
| [feed-score](./feed-score/) | AI news feed scoring, dedup, Markdown generation and publishing | v2.1.0 |
| [gemini-image-gen](./gemini-image-gen/) | Image generation and editing with Gemini API + provider fallback | v1.0.0 |
| [openclaw-usage-tracker](./openclaw-usage-tracker/) | Model usage and cost tracking with daily/range/full-history reports | v1.2.0 |
| [project-planner](./project-planner/) | Issue prioritization and task planning | v0.1.0 |
| [skill-validator](./skill-validator/) | Skill acceptance testing and cross-platform validation | v0.2.0 |
| [wechat-article-fetcher](./wechat-article-fetcher/) | Fetch and extract content from WeChat Official Account articles | v1.0.2 |
| [wechat-mp-publisher](./wechat-mp-publisher/) | Publish Markdown articles to WeChat Official Account draft box | v0.5.0 |

## Install

Add the repo as an extra skill directory in your OpenClaw config:

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

## Contributing

Each skill lives in its own directory with a `SKILL.md` file. Follow the [OpenClaw skill format](https://docs.openclaw.ai) for authoring new skills.

## License

MIT
