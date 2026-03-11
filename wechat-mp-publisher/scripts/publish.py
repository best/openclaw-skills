#!/usr/bin/env python3
# /// script
# dependencies = ["requests", "markdown-it-py", "beautifulsoup4"]
# ///
"""
WeChat MP Publisher - Push Markdown to WeChat Official Account draft box
"""
import os
import sys
import json
import argparse
import requests
import re
from pathlib import Path
from typing import Optional, Dict, List
from markdown_it import MarkdownIt
from bs4 import BeautifulSoup

# API endpoints
TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
UPLOAD_IMG_URL = "https://api.weixin.qq.com/cgi-bin/media/uploadimg"
UPLOAD_MATERIAL_URL = "https://api.weixin.qq.com/cgi-bin/material/add_material"
DRAFT_ADD_URL = "https://api.weixin.qq.com/cgi-bin/draft/add"


class WeChatMPPublisher:
    def __init__(self):
        self.app_id = os.getenv("WECHAT_APP_ID")
        self.app_secret = os.getenv("WECHAT_APP_SECRET")
        if not self.app_id or not self.app_secret:
            raise ValueError("WECHAT_APP_ID and WECHAT_APP_SECRET must be set")
        self.access_token: Optional[str] = None

    def get_access_token(self) -> str:
        if self.access_token:
            return self.access_token
        resp = requests.get(TOKEN_URL, params={
            "grant_type": "client_credential",
            "appid": self.app_id, "secret": self.app_secret
        })
        data = resp.json()
        if "access_token" not in data:
            raise Exception(f"Failed to get access_token: {data}")
        self.access_token = data["access_token"]
        return self.access_token

    def upload_image(self, image_path: str) -> str:
        token = self.get_access_token()
        with open(image_path, "rb") as f:
            resp = requests.post(
                f"{UPLOAD_IMG_URL}?access_token={token}", files={"media": f})
        data = resp.json()
        if "url" not in data:
            raise Exception(f"Failed to upload image: {data}")
        return data["url"]

    def upload_cover(self, image_path: str) -> str:
        token = self.get_access_token()
        with open(image_path, "rb") as f:
            resp = requests.post(
                f"{UPLOAD_MATERIAL_URL}?access_token={token}&type=image",
                files={"media": f})
        data = resp.json()
        if "media_id" not in data:
            raise Exception(f"Failed to upload cover: {data}")
        return data["media_id"]

    def convert_markdown(self, md_path: str) -> tuple[str, str, List[str]]:
        content = Path(md_path).read_text(encoding="utf-8")

        # Strip frontmatter
        title = "Untitled"
        body = content
        fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if fm_match:
            frontmatter = fm_match.group(1)
            body = content[fm_match.end():]
            t = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', frontmatter, re.MULTILINE)
            if t:
                title = t.group(1)

        if title == "Untitled":
            h1 = re.search(r'^#\s+(.+)$', body, re.MULTILINE)
            if h1:
                title = h1.group(1)

        # Extract image paths before conversion
        local_images = re.findall(r'!\[.*?\]\((.+?)\)', body)

        # Pre-process: fix bold markers that markdown-it can't parse
        # **text：**followed-by-text → **text：** followed-by-text (add space)
        # IMPORTANT: [^*\n]+? must NOT cross newlines, otherwise it pairs
        # the closing ** of one paragraph with the opening ** of the next
        body = re.sub(r'\*\*([^*\n]+?)\*\*(?=[^\s*])', r'**\1** ', body)

        # Pre-process: handle footnotes (markdown-it doesn't support [^N] syntax)
        # 1. Extract footnote definitions
        footnotes = {}
        def collect_footnote(m):
            footnotes[m.group(1)] = m.group(2).strip()
            return ''
        body = re.sub(r'^\[\^(\d+)\]:\s*(.+)$', collect_footnote, body, flags=re.MULTILINE)

        # Clean up orphaned --- that was between signature and footnotes
        body = re.sub(r'\n---\s*\n\s*$', '\n', body)

        # 2. Replace inline [^N] references with superscript
        body = re.sub(r'\[\^(\d+)\]', r'<sup>[\1]</sup>', body)

        # 3. Append formatted footnotes section if any exist
        if footnotes:
            fn_lines = ['<section style="margin-top:36px;padding-top:20px;border-top:1px solid #e5e5e5;">',
                         '<p style="font-size:14px;font-weight:600;color:#999;margin-bottom:10px;letter-spacing:1px;">参考文献</p>']
            for num in sorted(footnotes.keys(), key=int):
                # Strip markdown links to plain text (WeChat filters external URLs)
                text = footnotes[num]
                text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
                fn_lines.append(f'<p style="font-size:13px;color:#999;line-height:1.7;margin:4px 0;padding-left:1.5em;text-indent:-1.5em;">{num}. {text}</p>')
            fn_lines.append('</section>')
            body += '\n' + '\n'.join(fn_lines)

        # Convert with markdown-it (enable table support)
        md = MarkdownIt().enable('table')
        html = md.render(body)

        return title, html, local_images

    def replace_images_in_html(self, html: str, image_map: Dict[str, str]) -> str:
        soup = BeautifulSoup(html, 'html.parser')
        for img in soup.find_all('img'):
            src = img.get('src')
            if src and src in image_map:
                img['src'] = image_map[src]
        return str(soup)

    def style_html_for_wechat(self, html: str) -> str:
        soup = BeautifulSoup(html, 'html.parser')

        # Fix blockquote dialogue: add <br> before bold names for line breaks
        for bq in soup.find_all('blockquote'):
            for p in bq.find_all('p'):
                # Find all <strong> tags that start a dialogue line
                strongs = p.find_all('strong')
                for i, s in enumerate(strongs):
                    if i > 0 and s.string and ('：' in s.string or ':' in s.string):
                        s.insert_before(soup.new_tag('br'))

        # Remove empty list items
        for li in soup.find_all('li'):
            if not li.get_text(strip=True):
                li.decompose()

        # Unwrap <p> inside <li> (causes double spacing in WeChat)
        for li in soup.find_all('li'):
            for p in li.find_all('p'):
                p.unwrap()

        # Inline styles for WeChat (designed for light + dark mode compatibility)
        # Key: avoid subtle tinted backgrounds (invert badly in dark mode),
        # use clear contrasts, keep accent colors moderate saturation.
        style_map = {
            'h2': 'font-size:20px;font-weight:bold;color:#1a1a1a;margin:32px 0 16px;padding-bottom:10px;border-bottom:2px solid #07c160;',
            'h3': 'font-size:17px;font-weight:bold;color:#2c2c2c;margin:26px 0 12px;',
            'p': 'font-size:16px;color:#333;line-height:2;margin:16px 0;letter-spacing:0.5px;',
            'blockquote': 'border-left:3px solid #07c160;padding:14px 20px;margin:22px 0;color:#555;font-size:15px;line-height:1.85;',
            'strong': 'color:#1a1a1a;font-weight:600;',
            'em': 'color:#777;font-style:italic;',
            'ul': 'margin:14px 0;padding-left:24px;',
            'ol': 'margin:14px 0;padding-left:24px;',
            'li': 'font-size:16px;color:#333;line-height:2;margin:6px 0;letter-spacing:0.5px;',
            'img': 'max-width:100%;height:auto;display:block;margin:24px auto;border-radius:8px;',
            'table': 'width:100%;border-collapse:collapse;margin:20px 0;font-size:14px;',
            'th': 'border:1px solid #e0e0e0;padding:10px 14px;text-align:left;font-weight:bold;color:#333;',
            'td': 'border:1px solid #e0e0e0;padding:10px 14px;color:#555;line-height:1.6;',
            'hr': 'border:none;border-top:1px solid #e5e5e5;margin:36px 0;',
            'code': 'background:#f4f5f7;padding:2px 6px;border-radius:3px;font-size:14px;color:#476582;font-family:Consolas,monospace;',
            'pre': 'background:#1e1e2e;color:#cdd6f4;padding:18px;border-radius:8px;overflow-x:auto;margin:20px 0;line-height:1.6;font-size:14px;',
            'sup': 'font-size:11px;color:#07c160;vertical-align:super;line-height:0;',
        }

        for tag, style in style_map.items():
            for el in soup.find_all(tag):
                el['style'] = style + el.get('style', '')

        # pre > code: override inline code style
        for pre in soup.find_all('pre'):
            for code in pre.find_all('code'):
                code['style'] = 'font-size:14px;font-family:Consolas,monospace;color:#f8f8f2;background:none;'

        # Wrap in section
        wrapper = soup.new_tag('section')
        wrapper['style'] = 'padding:5px 0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB",sans-serif;'
        children = list(soup.children)
        for child in children:
            wrapper.append(child.extract() if hasattr(child, 'extract') else child)

        return str(wrapper)

    def create_draft(self, title: str, content: str, cover_media_id: str,
                     author: str = "张昊辰(Astralor)", source_url: str = "") -> Dict:
        token = self.get_access_token()
        if len(title) > 32:
            title = title[:31] + "…"

        payload = {
            "articles": [{
                "title": title,
                "author": author,
                "content": content,
                "thumb_media_id": cover_media_id,
                "need_open_comment": 1,
                "only_fans_can_comment": 0,
                "content_source_url": source_url or ""
            }]
        }

        resp = requests.post(
            f"{DRAFT_ADD_URL}?access_token={token}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        data = resp.json()

        if data.get("errcode", 0) != 0:
            raise Exception(f"Failed to create draft: {data}")
        return data

    def publish(self, md_path: str, cover_path: Optional[str] = None,
                title_override: Optional[str] = None, source_url: str = ""):
        print(f"📄 Reading {md_path}...")
        title, html, local_images = self.convert_markdown(md_path)
        if title_override:
            title = title_override

        # Upload images
        image_map = {}
        md_dir = Path(md_path).parent
        for img_path in local_images:
            if img_path.startswith(('http://', 'https://')):
                continue
            full_path = (md_dir / img_path).resolve()
            if not full_path.exists():
                print(f"⚠️  Image not found: {img_path}")
                continue
            print(f"📤 Uploading {img_path}...")
            cdn_url = self.upload_image(str(full_path))
            image_map[img_path] = cdn_url

        html = self.replace_images_in_html(html, image_map)
        html = self.style_html_for_wechat(html)

        # Cover
        if not cover_path and local_images:
            first = local_images[0]
            if not first.startswith(('http://', 'https://')):
                cover_path = str((md_dir / first).resolve())
        if not cover_path:
            raise ValueError("No cover image. Use --cover.")

        print(f"📸 Uploading cover...")
        cover_media_id = self.upload_cover(cover_path)

        print(f"✍️  Creating draft: {title}...")
        result = self.create_draft(title, html, cover_media_id, source_url=source_url)

        print(f"✅ Draft created! media_id: {result.get('media_id')}")
        print("👉 Go to mp.weixin.qq.com to review and publish.")


def main():
    parser = argparse.ArgumentParser(description="Publish Markdown to WeChat MP")
    parser.add_argument("-f", "--file", required=True, help="Markdown file path")
    parser.add_argument("-c", "--cover", help="Cover image path")
    parser.add_argument("-t", "--title", help="Override title")
    parser.add_argument("-u", "--url", help="Original article URL", default="")
    args = parser.parse_args()

    try:
        publisher = WeChatMPPublisher()
        publisher.publish(args.file, args.cover, title_override=args.title, source_url=args.url)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
