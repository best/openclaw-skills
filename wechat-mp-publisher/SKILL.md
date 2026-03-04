---
name: wechat-mp-publisher
version: 0.1.0
description: "Publish Markdown articles to WeChat Official Account draft box. Use when user wants to push blog posts to 微信公众号, convert Markdown to WeChat format, or create 公众号草稿."
---

# WeChat MP Publisher

Publish Markdown articles to WeChat Official Account (微信公众号) draft box.

## Usage

```bash
uv run <skill_dir>/scripts/publish.py -f <markdown-file>
```

The script:
1. Gets access_token from WeChat API
2. Extracts and uploads images to WeChat CDN
3. Converts Markdown to WeChat-compatible HTML
4. Uploads cover image as permanent material
5. Creates draft via `draft/add` API

## Environment Variables

Required (set in `env.vars`):
- `WECHAT_APP_ID` — 公众号 AppID
- `WECHAT_APP_SECRET` — 公众号 AppSecret

## Output

Draft created in WeChat MP backend (mp.weixin.qq.com). User confirms and publishes manually.

## Limitations

- Personal subscription accounts cannot auto-publish via API (requires manual confirmation)
- Images must be uploaded to WeChat CDN (external URLs filtered)
- Content size limit: 2MB, <20k characters
