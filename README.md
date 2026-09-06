# openclaw-skills

English | [中文](./README_CN.md)

OpenClaw agent skills for autonomous development workflows.

> This repository is self-maintained by an OpenClaw agent through continuous PCEC (Plan-Check-Evolve-Commit) evolution cycles.

## Skills

| Skill | Description | Version |
|-------|-------------|---------|
| [cc-iterator](./cc-iterator/) | Autonomous coding agent iteration loop | v0.1.4 |
| [chevereto-upload](./chevereto-upload/) | Image upload and management for Chevereto V4 instances | v0.4.1 |
| [code-reviewer](./code-reviewer/) | Standardized code review quality gate | v0.1.2 |
| [dream](./dream/) | Memory methodology & consolidation with OpenClaw T0 budget guard, 4-action model, 3 flows, dream diary, and fact-review audit | v2.5.3 |
| [discord-thread-archiver](./discord-thread-archiver/) | Smart Discord thread archiving with AI judgment | v1.3.3 |
| [evolution-engine](./evolution-engine/) | PCEC — Wiki-Native evolution engine with Gene/Capsule knowledge reuse | v2.1.3 |
| [feed-collect](./feed-collect/) | AI news feed collection via deterministic feedctl runner | v2.3.1 |
| [feed-broadcast](./feed-broadcast/) | AI Feed broadcast via controlled wrapper and delivery guards | v1.3.0 |
| [feed-score](./feed-score/) | AI Feed scoring via controlled runner and validated publish flow | v2.4.0 |
| [gemini-image-gen](./gemini-image-gen/) | Image generation/editing with Gemini API using GEMINI_IMAGE_CONFIG provider chain | v1.1.2 |
| [openai-image-gen](./openai-image-gen/) | Image generation/editing with OpenAI Image API using OPENAI_IMAGE_CONFIG provider chain | v1.2.1 |
| [openclaw-usage-tracker](./openclaw-usage-tracker/) | Native model usage and cost reports with completeness checks | v1.4.3 |
| [project-planner](./project-planner/) | Issue prioritization and task planning | v0.1.0 |
| [skill-validator](./skill-validator/) | Skill acceptance testing and cross-platform validation | v0.2.5 |
| [wechat-article-fetcher](./wechat-article-fetcher/) | Fetch and extract content from WeChat Official Account articles | v1.0.3 |
| [wechat-mp-publisher](./wechat-mp-publisher/) | Publish Markdown articles to WeChat Official Account draft box | v0.6.1 |

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
