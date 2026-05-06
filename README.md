# openclaw-skills

English | [中文](./README_CN.md)

OpenClaw agent skills for autonomous development workflows.

> This repository is self-maintained by an OpenClaw agent through continuous PCEC (Plan-Check-Evolve-Commit) evolution cycles.

## Skills

| Skill | Description | Version |
|-------|-------------|---------|
| [cc-iterator](./cc-iterator/) | Autonomous coding agent iteration loop | v0.1.4 |
| [chevereto-upload](./chevereto-upload/) | Image upload and management for Chevereto V4 instances | v0.4.0 |
| [code-reviewer](./code-reviewer/) | Standardized code review quality gate | v0.1.2 |
| [dream](./dream/) | Memory methodology & consolidation with OpenClaw T0 budget guard, 4-action model, 3 flows, dream diary, and fact-review audit | v2.5.2 |
| [discord-thread-archiver](./discord-thread-archiver/) | Smart Discord thread archiving with AI judgment | v1.1.1 |
| [evolution-engine](./evolution-engine/) | PCEC — Wiki-Native evolution engine with Gene/Capsule knowledge reuse | v2.1.1 |
| [feed-collect](./feed-collect/) | AI news feed collection via Miniflux local config + HN + GitHub Trending | v2.1.0 |
| [feed-broadcast](./feed-broadcast/) | AI news feed smart broadcast with push/skip judgment | v1.1.1 |
| [feed-score](./feed-score/) | AI news feed scoring, dedup, Markdown generation and publishing | v2.1.3 |
| [gemini-image-gen](./gemini-image-gen/) | Image generation/editing with Gemini API using GEMINI_IMAGE_CONFIG provider chain | v1.1.1 |
| [openai-image-gen](./openai-image-gen/) | Image generation/editing with OpenAI Image API using OPENAI_IMAGE_CONFIG provider chain | v1.2.0 |
| [openclaw-usage-tracker](./openclaw-usage-tracker/) | Model usage and cost tracking with daily/range/full-history reports | v1.2.0 |
| [project-planner](./project-planner/) | Issue prioritization and task planning | v0.1.0 |
| [skill-validator](./skill-validator/) | Skill acceptance testing and cross-platform validation | v0.2.1 |
| [wechat-article-fetcher](./wechat-article-fetcher/) | Fetch and extract content from WeChat Official Account articles | v1.0.2 |
| [wechat-mp-publisher](./wechat-mp-publisher/) | Publish Markdown articles to WeChat Official Account draft box | v0.6.0 |

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

Store skill versions in `SKILL.md` frontmatter under `metadata.version` (not top-level `version`) and keep the table above in sync.

## License

MIT
