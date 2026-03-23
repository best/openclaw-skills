#!/usr/bin/env python3
"""
Generate blog post .md files from scored results JSON.

Usage:
  python3 generate-posts.py <scored-results.json> [--repo-dir DIR]

Reads scored-results.json, generates .md files for all "publish" entries.
Outputs summary of generated files.
"""

import json
import sys
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path


def sanitize_yaml(s):
    """Make string safe for YAML double-quoted values."""
    if not s:
        return ""
    s = s.replace('"', '「').replace('\n', ' ').replace('\\', '\\\\')
    return s


def get_next_seq(blog_dir, date_str):
    """Get next sequence number for the given date directory."""
    day_dir = blog_dir / date_str
    if not day_dir.exists():
        return 1
    nums = []
    for f in day_dir.iterdir():
        if f.suffix == '.md':
            m = re.match(r'^(\d+)-', f.name)
            if m:
                nums.append(int(m.group(1)))
    return max(nums) + 1 if nums else 1


def validate_breakdown(bd):
    """Validate scoreBreakdown format."""
    required = ['信息增量:', '内容质量:', '实用价值:', '减分:']
    return all(k in bd for k in required)


def generate_post(article, seq, blog_dir, date_str):
    """Generate a single .md blog post file. Returns (filepath, error)."""
    slug = article.get('slug', 'untitled')
    filename = f"{seq:03d}-{slug}.md"
    day_dir = blog_dir / date_str
    day_dir.mkdir(parents=True, exist_ok=True)
    filepath = day_dir / filename

    # Validate scoreBreakdown
    breakdown = article.get('scoreBreakdown', '')
    if not validate_breakdown(breakdown):
        return None, f"Invalid scoreBreakdown: {breakdown}"

    # Build frontmatter
    fm_lines = [
        '---',
        f'title: "{sanitize_yaml(article["title"])}"',
        f'description: "{sanitize_yaml(article.get("description", ""))}"',
        f'pubDatetime: {article.get("pubDatetime", "")}',
        f'collectedAt: {article.get("collectedAt", "")}',
        f'category: "{article.get("category", "行业动态")}"',
        f'tags: {json.dumps(article.get("tags", []), ensure_ascii=False)}',
        f'featured: {"true" if article.get("featured") else "false"}',
        f'score: {article.get("score", 0)}',
        f'scoreReason: "{sanitize_yaml(article.get("scoreReason", ""))}"',
        f'scoreBreakdown: "{breakdown}"',
        f'sourceUrl: "{article.get("sourceUrl", article.get("url", ""))}"',
        f'sourceType: "{article.get("sourceType", "other")}"',
        f'sourceName: "{sanitize_yaml(article.get("sourceName", ""))}"',
        f'ogImage: ""',
        '---',
    ]

    # Build blockquote header
    score = article.get('score', 0)
    src_name = article.get('sourceName', '')
    src_url = article.get('sourceUrl', article.get('url', ''))
    pub_date = article.get('pubDatetime', '')[:10]
    reason = article.get('scoreReason', '')

    header = (
        f'> **评分 {score}** · 来源：[{src_name}]({src_url}) · 发布于 {pub_date}\n'
        f'>\n'
        f'> 评分依据：{reason}'
    )

    body = article.get('body', '')

    content = '\n'.join(fm_lines) + f'\n\n{header}\n\n{body}\n'
    filepath.write_text(content, encoding='utf-8')
    return filepath, None


def main():
    if len(sys.argv) < 2:
        print("Usage: generate-posts.py <scored-results.json> [--repo-dir DIR]",
              file=sys.stderr)
        sys.exit(1)

    results_path = sys.argv[1]
    repo_dir = Path('/data/code/github.com/astralor/feed')

    if '--repo-dir' in sys.argv:
        idx = sys.argv.index('--repo-dir')
        repo_dir = Path(sys.argv[idx + 1])

    with open(results_path) as f:
        data = json.load(f)

    results = data.get('results', [])
    publish = [r for r in results if r.get('verdict') == 'publish']
    skip = [r for r in results if r.get('verdict') == 'skip']

    if not publish:
        print(json.dumps({
            "generated": 0,
            "skipped": len(skip),
            "files": []
        }))
        sys.exit(0)

    blog_dir = repo_dir / 'src' / 'data' / 'blog'
    cst = timezone(timedelta(hours=8))
    today = datetime.now(cst).strftime('%Y-%m-%d')

    seq = get_next_seq(blog_dir, today)
    generated = []
    errors = []

    for article in publish:
        filepath, err = generate_post(article, seq, blog_dir, today)
        if err:
            errors.append({'title': article.get('title', '?'), 'error': err})
            continue
        generated.append({
            'file': str(filepath.relative_to(repo_dir)),
            'title': article['title'],
            'score': article.get('score', 0),
        })
        seq += 1

    # Output structured summary
    summary = {
        "generated": len(generated),
        "skipped": len(skip),
        "errors": len(errors),
        "files": generated,
    }
    if errors:
        summary["errorDetails"] = errors

    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if errors:
        sys.exit(1)


if __name__ == '__main__':
    main()
