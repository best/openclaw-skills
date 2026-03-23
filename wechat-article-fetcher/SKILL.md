---
name: wechat-article-fetcher
description: Fetch and extract content from WeChat Official Account (微信公众号) articles. Use when a user provides a mp.weixin.qq.com URL and wants to read, extract, summarize, or archive the article. Supports full text extraction, metadata (title, account name, author, publish time), and image downloading. Also use when comparing WeChat article content or ingesting 公众号 articles into other workflows.
version: 1.0.2
---

# WeChat Article Fetcher

Extract full content from WeChat Official Account articles via `mp.weixin.qq.com` URLs.

## How It Works

WeChat article pages are server-side rendered. `curl` with a browser User-Agent bypasses WeChat's bot detection. Images require an additional `Referer: https://mp.weixin.qq.com/` header.

`web_fetch` does NOT work — WeChat returns a "环境异常" verification page.

## Usage

Run the extraction script:

```bash
python3 scripts/fetch_article.py "<url>" [--output-dir /tmp/wx_article] [--images] [--json]
```

**Arguments:**
- `url` — WeChat article URL (`https://mp.weixin.qq.com/s/xxx`)
- `--output-dir` — Output directory (default: `/tmp/wx_article`)
- `--images` — Also download all embedded images
- `--json` — Print metadata JSON to stdout

**Output files:**
- `article.md` — Full article as Markdown with YAML frontmatter (title, account, date, source URL)
- `meta.json` — Structured metadata (title, account, author, publish_time, image_count, char_count)
- `images/` — Downloaded images as `img_001.jpg`, `img_002.png`, etc. (only with `--images`)

## Extracted Metadata

| Field | Source |
|-------|--------|
| title | `var msg_title` / `og:title` meta tag |
| account | `#js_name` element / `var nickname` |
| author | `#js_author_name` element |
| publish_time | `var ct` (Unix timestamp) |
| biz | `var biz` (account identifier) |
| cover_url | `var msg_cdn_url` |

## Limitations

- **Single article only** — cannot list or search articles from an account (requires login)
- **No reading counts** — view/like counts require authenticated API
- **Rate limiting** — WeChat may block IPs with excessive requests; space out batch fetches
- **Verification page** — if WeChat returns "环境异常", wait and retry (script detects this and exits with error)
- **Table rendering** — HTML tables are converted to plain text (WeChat often renders tables as images anyway)
