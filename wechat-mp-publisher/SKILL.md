---
name: wechat-mp-publisher
version: 0.4.0
description: "Publish Markdown articles to WeChat Official Account draft box. Use when user wants to push blog posts to 微信公众号, convert Markdown to WeChat format, or create 公众号草稿."
---

# WeChat MP Publisher

Publish Markdown articles to WeChat Official Account (微信公众号) draft box.

## Usage

```bash
uv run <skill_dir>/scripts/publish.py -f <markdown-file> [-u <source-url>] [-c <cover-image>] [-t <title-override>] [-a <author>]
```

The script:
1. Gets access_token from WeChat API
2. Pre-processes Markdown: footnotes → superscript references + "参考文献" section, bold fix
3. Extracts and uploads images to WeChat CDN
4. Converts Markdown to WeChat-compatible HTML with inline styles
5. Uploads cover image as permanent material
6. Creates draft via `draft/add` API

## Options

- `-f, --file` — Markdown file path (required)
- `-u, --url` — Original article URL (set as "阅读原文" link)
- `-c, --cover` — Cover image path (defaults to first image in article)
- `-t, --title` — Override title (defaults to frontmatter title)
- `-a, --author` — Author name (defaults to "张昊辰(Astralor)")

## Environment Variables

Required (set in `env.vars`):
- `WECHAT_APP_ID` — 公众号 AppID
- `WECHAT_APP_SECRET` — 公众号 AppSecret

## Markdown Features Supported

- **Footnotes**: `[^N]` references become green superscript numbers; definitions at bottom become styled "参考文献" section with small gray text. External links in footnotes are converted to plain text (WeChat filters external URLs).
- **Bold**: Handles `**text**immediately-followed` patterns that markdown-it can't parse.
- **Images**: Local images uploaded to WeChat CDN; external URLs kept as-is.
- **Code blocks**: Dark theme (Catppuccin-inspired), inline code in blue-gray.
- **Tables**: Fully styled with borders and alternating header.

## Style Design

Optimized for both light and dark mode reading:
- No tinted backgrounds (they invert poorly in dark mode)
- Green accent (#07c160) for h2 underline, superscript refs, bold text (#2e7d32)
- Code blocks use dark background that stays dark in dark mode
- Images have no box-shadow (shadows look odd when inverted)

## Output

Draft created in WeChat MP backend (mp.weixin.qq.com). User confirms and publishes manually.

## Known Gotchas

- **Bold regex cross-line bug (v0.2.0 fix)**: The bold pre-processor uses `[^*\n]+?` (not `[^*]+?`) to prevent matching across paragraph boundaries. Without the `\n` exclusion, `**end of paragraph` pairs with `beginning of next**`, corrupting entire sections.
- **Orphaned `---` separators**: If the source Markdown has a horizontal rule between content and footnote definitions, the footnote extraction leaves an orphan `---`. The script cleans trailing `\n---\n` before rendering.
- **WeChat external URL filtering**: All `[text](url)` links in footnotes are stripped to plain text because WeChat silently drops external links from article content.
- **Inline code layout break (v0.3.0 fix)**: Inline `<code>` elements without explicit `display:inline` may be rendered as inline-block on WeChat mobile, causing surrounding text to break with large gaps. The style now includes `display:inline;word-break:break-all;line-height:inherit;`.
- **Bold preprocessor breaks list items (v0.4.0 fix)**: The bold regex `**text**：` added a space before CJK punctuation (`**text** ：`), causing WeChat to render extra visual gaps in list items. Fixed by excluding CJK punctuation (U+3000-303F, U+FF00-FFEF) from the lookahead.
- **Code block whitespace (v0.4.0 fix)**: `<pre>` blocks lacked `white-space:pre-wrap`, causing indentation and line breaks to collapse in WeChat. Code block colors updated from Catppuccin to One Dark (#282c34) for better readability.

## Limitations

- Personal subscription accounts cannot auto-publish via API (requires manual confirmation)
- Images must be uploaded to WeChat CDN (external URLs filtered)
- Content size limit: 2MB, <20k characters
- Each push creates a new draft; old drafts must be manually deleted
- WeChat title limit: 64 characters (auto-truncated with …)
