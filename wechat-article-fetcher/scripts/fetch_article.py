#!/usr/bin/env python3
"""
Fetch and extract content from a WeChat Official Account (公众号) article.

Usage:
    python3 fetch_article.py <url> [--output-dir <dir>] [--images] [--json]

Arguments:
    url             WeChat article URL (mp.weixin.qq.com/s/xxx)
    --output-dir    Directory to save output files (default: /tmp/wx_article)
    --images        Also download all images
    --json          Output metadata as JSON to stdout

Output:
    - article.md    Clean Markdown content
    - meta.json     Article metadata (title, account, time, image count)
    - images/       Downloaded images (if --images)
"""

import argparse
import datetime
import html as html_mod
import json
import os
import re
import subprocess
import sys

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def fetch_html(url: str) -> str:
    """Fetch article HTML via curl with browser UA."""
    result = subprocess.run(
        [
            "curl", "-s", "-L",
            "-H", f"User-Agent: {UA}",
            url,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        print(f"Error: curl failed with code {result.returncode}", file=sys.stderr)
        sys.exit(1)
    return result.stdout


def extract_meta(content: str) -> dict:
    """Extract article metadata from HTML."""
    meta = {}

    # Title - try multiple patterns
    for pat in [
        r"var msg_title = '([^']*)'",
        r'var msg_title = "([^"]*)"',
        r'<meta property="og:title" content="([^"]*)"',
    ]:
        m = re.search(pat, content)
        if m and m.group(1).strip():
            meta["title"] = html_mod.unescape(m.group(1).strip())
            break

    # Account name
    for pat in [
        r'id="js_name"[^>]*>(.*?)</',
        r"var nickname = '([^']*)'",
        r'var nickname = "([^"]*)"',
    ]:
        m = re.search(pat, content, re.DOTALL)
        if m and m.group(1).strip():
            meta["account"] = html_mod.unescape(m.group(1).strip())
            break

    # Publish timestamp
    m = re.search(r'var ct = "(\d+)"', content)
    if m:
        ts = int(m.group(1))
        meta["publish_time"] = datetime.datetime.fromtimestamp(ts).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        meta["publish_timestamp"] = ts

    # Biz ID (account identifier)
    m = re.search(r"var biz = '([^']*)'", content)
    if not m:
        m = re.search(r'var biz = "([^"]*)"', content)
    if m:
        meta["biz"] = m.group(1)

    # Author
    m = re.search(r'id="js_author_name"[^>]*>(.*?)</', content, re.DOTALL)
    if m and m.group(1).strip():
        meta["author"] = html_mod.unescape(m.group(1).strip())

    # Cover image
    m = re.search(r'var msg_cdn_url = "([^"]*)"', content)
    if not m:
        m = re.search(r"var msg_cdn_url = '([^']*)'", content)
    if m:
        meta["cover_url"] = m.group(1)

    return meta


def extract_image_urls(content: str) -> list:
    """Extract all image URLs from the article body."""
    urls = []
    seen = set()

    # data-src is the primary image source in WeChat articles
    for url in re.findall(r'data-src="(https://mmbiz\.qpic\.cn/[^"]+)"', content):
        if url not in seen:
            urls.append(url)
            seen.add(url)

    return urls


def download_image(url: str, output_path: str) -> bool:
    """Download a single image with proper headers."""
    result = subprocess.run(
        [
            "curl", "-s", "-L",
            "-o", output_path,
            "-H", f"User-Agent: {UA}",
            "-H", "Referer: https://mp.weixin.qq.com/",
            url,
        ],
        capture_output=True,
        timeout=30,
    )
    return result.returncode == 0 and os.path.getsize(output_path) > 0


def html_to_markdown(body_html: str, image_urls: list = None) -> str:
    """Convert article body HTML to clean Markdown."""
    text = body_html

    # Decode JS-escaped HTML if present
    text = text.replace("\\x3c", "<").replace("\\x3e", ">")
    text = text.replace("\\x22", '"').replace("\\x26nbsp;", " ")

    # Block elements → newlines
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"</p>", "\n\n", text)
    text = re.sub(r"</li>", "\n", text)
    text = re.sub(r"</section>", "\n", text)
    text = re.sub(r"<hr[^>]*/?\s*>", "\n---\n", text)

    # Headers
    for i in range(1, 7):
        text = re.sub(rf"<h{i}[^>]*>", f"\n\n{'#' * i} ", text)
        text = re.sub(rf"</h{i}>", "\n\n", text)

    # Inline formatting
    text = re.sub(r"<strong[^>]*>", "**", text)
    text = re.sub(r"</strong>", "**", text)
    text = re.sub(r"<b[^>]*>", "**", text)
    text = re.sub(r"</b>", "**", text)
    text = re.sub(r"<em[^>]*>", "*", text)
    text = re.sub(r"</em>", "*", text)

    # Code blocks: WeChat wraps each line in <code> inside <pre>.
    # First, handle <pre> blocks: strip inner <code> tags, then wrap in fenced blocks.
    def pre_replace(m):
        inner = m.group(1)
        # Each <code> block is one line in WeChat's code snippets
        inner = re.sub(r"<br\s*/?>", "\n", inner)
        # Replace </code><code> boundaries with newlines
        inner = re.sub(r"</code>\s*<code[^>]*>", "\n", inner)
        # Remove remaining <code> wrappers
        inner = re.sub(r"</?code[^>]*>", "", inner)
        # Strip other tags inside pre
        inner = re.sub(r"<[^>]+>", "", inner)
        inner = html_mod.unescape(inner)
        # Clean up whitespace per line
        lines = inner.split("\n")
        lines = [l.rstrip() for l in lines if l.strip()]
        return "\n```\n" + "\n".join(lines) + "\n```\n"

    text = re.sub(r"<pre[^>]*>(.*?)</pre>", pre_replace, text, flags=re.DOTALL)

    # Inline code (outside of pre blocks)
    text = re.sub(r"<code[^>]*>", "`", text)
    text = re.sub(r"</code>", "`", text)

    # Images → markdown image syntax
    img_index = [0]
    def img_replace(m):
        tag = m.group(0)
        # Get data-src (real URL)
        src_m = re.search(r'data-src="([^"]*)"', tag)
        alt_m = re.search(r'alt="([^"]*)"', tag)
        src = src_m.group(1) if src_m else ""
        alt = html_mod.unescape(alt_m.group(1)) if alt_m and alt_m.group(1) else ""

        img_index[0] += 1
        if src:
            return f"![{alt or f'图片{img_index[0]}'}]({src})"
        return f"[图片{img_index[0]}]"

    text = re.sub(r"<img[^>]*/?>", img_replace, text)

    # Links: convert <a href="url">text</a> to [text](url)
    def link_full_replace(m):
        href = m.group(1)
        link_text = re.sub(r"<[^>]+>", "", m.group(2))  # strip inner tags
        link_text = html_mod.unescape(link_text.strip())
        if href and link_text:
            return f"[{link_text}]({href})"
        return link_text or ""

    text = re.sub(
        r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
        link_full_replace, text, flags=re.DOTALL,
    )
    # Strip any remaining <a> tags (those without href)
    text = re.sub(r"<a[^>]*>", "", text)
    text = re.sub(r"</a>", "", text)

    # Strip remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Decode HTML entities
    text = html_mod.unescape(text)

    # Clean whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove trailing JS noise
    for marker in ["var first_sceen__time", "预览时标签不可点"]:
        idx = text.find(marker)
        if idx > 0:
            text = text[:idx]

    return text.strip()


def extract_body(content: str) -> str:
    """Extract the article body HTML from the full page."""
    # Try multiple ending markers, from most specific to least
    for end_pattern in [
        r'<div class="rich_media_tool"',
        r'<div id="js_tags"',
        r'<div class="rich_media_area_extra"',
        r'<div class="like_area"',
        r'<div id="js_pc_qr_code"',
    ]:
        m = re.search(
            rf'id="js_content"[^>]*>(.*?){end_pattern}',
            content,
            re.DOTALL,
        )
        if m:
            return m.group(1)

    # Fallback: just grab from js_content to next major div
    m = re.search(r'id="js_content"[^>]*>(.*?)</div>\s*<div', content, re.DOTALL)
    if m:
        return m.group(1)

    return ""


def main():
    parser = argparse.ArgumentParser(description="Fetch WeChat article content")
    parser.add_argument("url", help="WeChat article URL")
    parser.add_argument(
        "--output-dir", default="/tmp/wx_article", help="Output directory"
    )
    parser.add_argument("--images", action="store_true", help="Download images")
    parser.add_argument("--json", action="store_true", help="Output JSON to stdout")
    args = parser.parse_args()

    # Validate URL
    if "mp.weixin.qq.com" not in args.url:
        print("Error: URL must be from mp.weixin.qq.com", file=sys.stderr)
        sys.exit(1)

    # Fetch
    print("Fetching article...", file=sys.stderr)
    raw_html = fetch_html(args.url)

    if not raw_html or len(raw_html) < 1000:
        print("Error: Failed to fetch article (empty or too short)", file=sys.stderr)
        sys.exit(1)

    # Check for error pages
    if "环境异常" in raw_html[:10000]:
        print(
            "Error: WeChat returned a verification page. Try again later.",
            file=sys.stderr,
        )
        sys.exit(1)

    if "参数错误" in raw_html[:10000]:
        print("Error: Invalid article URL (参数错误).", file=sys.stderr)
        sys.exit(1)

    if "已被发布者删除" in raw_html[:30000] and "js_content" not in raw_html:
        print("Error: Article has been deleted by publisher.", file=sys.stderr)
        sys.exit(1)

    if "此内容因违规无法查看" in raw_html[:30000] and "js_content" not in raw_html:
        print("Error: Article removed for policy violation.", file=sys.stderr)
        sys.exit(1)

    # Extract metadata
    meta = extract_meta(raw_html)

    # Extract body
    body_html = extract_body(raw_html)
    if not body_html:
        print("Error: Could not find article body", file=sys.stderr)
        sys.exit(1)

    # Extract image URLs
    image_urls = extract_image_urls(body_html)
    meta["image_count"] = len(image_urls)

    # Convert to Markdown
    markdown = html_to_markdown(body_html, image_urls)
    meta["char_count"] = len(markdown)

    # Prepare output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Write Markdown — escape double quotes in YAML values to prevent injection
    def yaml_escape(val: str) -> str:
        """Escape a string for use in YAML double-quoted scalars."""
        return val.replace("\\", "\\\\").replace('"', '\\"')

    md_header = f"""---
title: "{yaml_escape(meta.get('title', 'Untitled'))}"
account: "{yaml_escape(meta.get('account', 'Unknown'))}"
author: "{yaml_escape(meta.get('author', ''))}"
date: "{yaml_escape(meta.get('publish_time', ''))}"
source: "{yaml_escape(args.url)}"
---

"""
    md_path = os.path.join(args.output_dir, "article.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_header + markdown)

    # Download images if requested
    if args.images and image_urls:
        img_dir = os.path.join(args.output_dir, "images")
        os.makedirs(img_dir, exist_ok=True)
        downloaded = 0
        for i, url in enumerate(image_urls):
            # Determine extension from URL
            ext = "jpg"
            if "wx_fmt=png" in url:
                ext = "png"
            elif "wx_fmt=gif" in url:
                ext = "gif"
            elif "wx_fmt=webp" in url:
                ext = "webp"

            img_path = os.path.join(img_dir, f"img_{i + 1:03d}.{ext}")
            if download_image(url, img_path):
                downloaded += 1
                print(f"  Downloaded image {i + 1}/{len(image_urls)}", file=sys.stderr)
            else:
                print(
                    f"  Failed to download image {i + 1}/{len(image_urls)}",
                    file=sys.stderr,
                )

        meta["images_downloaded"] = downloaded

    # Write metadata
    meta_path = os.path.join(args.output_dir, "meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # Output
    if args.json:
        print(json.dumps(meta, ensure_ascii=False, indent=2))
    else:
        print(f"\n✅ Article extracted successfully!", file=sys.stderr)
        print(f"  Title:   {meta.get('title', 'N/A')}", file=sys.stderr)
        print(f"  Account: {meta.get('account', 'N/A')}", file=sys.stderr)
        print(f"  Time:    {meta.get('publish_time', 'N/A')}", file=sys.stderr)
        print(f"  Length:  {meta.get('char_count', 0)} chars", file=sys.stderr)
        print(f"  Images:  {meta.get('image_count', 0)}", file=sys.stderr)
        print(f"  Output:  {args.output_dir}/", file=sys.stderr)


if __name__ == "__main__":
    main()
