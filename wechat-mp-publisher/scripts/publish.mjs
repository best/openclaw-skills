#!/usr/bin/env node
/**
 * WeChat MP Publisher — Push Markdown to WeChat Official Account draft box
 * Uses @wenyan-md/core for WeChat-compatible HTML rendering
 */

import { renderStyledContent } from "@wenyan-md/core/wrapper";
import fs from "fs";
import path from "path";
import { parseArgs } from "util";

const WECHAT_API = "https://api.weixin.qq.com/cgi-bin";

// === Config ===
const APP_ID = process.env.WECHAT_APP_ID;
const APP_SECRET = process.env.WECHAT_APP_SECRET;
if (!APP_ID || !APP_SECRET) {
  console.error("❌ WECHAT_APP_ID and WECHAT_APP_SECRET must be set");
  process.exit(1);
}

// === WeChat API helpers ===
let cachedToken = null;

async function getAccessToken() {
  if (cachedToken) return cachedToken;
  const url = `${WECHAT_API}/token?grant_type=client_credential&appid=${APP_ID}&secret=${APP_SECRET}`;
  const res = await fetch(url);
  const data = await res.json();
  if (!data.access_token) throw new Error(`Failed to get token: ${JSON.stringify(data)}`);
  cachedToken = data.access_token;
  return cachedToken;
}

async function uploadInlineImage(localPath, accessToken) {
  const buffer = fs.readFileSync(localPath);
  const ext = path.extname(localPath).toLowerCase();
  const mimeType = ext === ".png" ? "image/png" : "image/jpeg";
  const form = new FormData();
  form.append("media", new Blob([buffer], { type: mimeType }), path.basename(localPath));
  const res = await fetch(`${WECHAT_API}/media/uploadimg?access_token=${accessToken}`, {
    method: "POST", body: form
  });
  const data = await res.json();
  if (!data.url) throw new Error(`Failed to upload image: ${JSON.stringify(data)}`);
  return data.url;
}

async function uploadCover(localPath, accessToken) {
  const buffer = fs.readFileSync(localPath);
  const ext = path.extname(localPath).toLowerCase();
  const mimeType = ext === ".png" ? "image/png" : "image/jpeg";
  const form = new FormData();
  form.append("media", new Blob([buffer], { type: mimeType }), path.basename(localPath));
  const res = await fetch(`${WECHAT_API}/material/add_material?access_token=${accessToken}&type=image`, {
    method: "POST", body: form
  });
  const data = await res.json();
  if (!data.media_id) throw new Error(`Failed to upload cover: ${JSON.stringify(data)}`);
  return data.media_id;
}

// === Markdown processing ===
function extractFrontmatter(markdown) {
  const match = markdown.match(/^---\s*\n([\s\S]*?)\n---\s*\n/);
  if (!match) return { title: null, image: null, body: markdown };
  const fm = match[1];
  const titleMatch = fm.match(/^title:\s*["']?(.+?)["']?\s*$/m);
  const imageMatch = fm.match(/^image:\s*["']?(.+?)["']?\s*$/m);
  return {
    title: titleMatch ? titleMatch[1] : null,
    image: imageMatch ? imageMatch[1] : null,
    body: markdown.slice(match[0].length)
  };
}

// Module-level: footnotes extracted during preprocessing, consumed by buildFootnotesHtml()
let _pendingFootnotes = null;

// Pre-process markdown before sending to wenyan-md
// IMPORTANT: Do NOT modify ** bold markers — wenyan-md handles 50/53 cases correctly
// The remaining 3 cases (**text：**followedByText) are fixed in HTML post-processing
function preprocessMarkdown(body) {
  const footnotes = new Map();

  // Extract and remove [^N]: footnote definitions
  // Convert markdown links inside to plain text so wenyan-md won't double-footnote them
  body = body.replace(/^\[\^(\d+)\]:\s*(.+)$/gm, (_match, num, text) => {
    const cleaned = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '$1: $2');
    footnotes.set(Number(num), cleaned);
    return '';
  });

  // Remove "**参考文献**" heading and the --- separator before it
  // (we render our own styled heading in buildFootnotesHtml)
  body = body.replace(/\n---\n+\*\*参考文献\*\*\n*/g, '\n');

  // Replace [^N] references in body with superscript HTML
  body = body.replace(/\[\^(\d+)\]/g, '<sup>[$1]</sup>');

  // Clean up excessive blank lines left by removed definitions
  body = body.replace(/\n{3,}/g, '\n\n');

  _pendingFootnotes = footnotes.size > 0 ? footnotes : null;
  return body;
}

// Build HTML footnote section from extracted [^N] definitions
// Call after postProcess(); returns empty string if no footnotes were extracted
function buildFootnotesHtml() {
  if (!_pendingFootnotes) return '';
  const sorted = [..._pendingFootnotes.entries()].sort((a, b) => a[0] - b[0]);
  let html = '<section id="footnotes" style="margin-top:1.5em;padding-top:0.8em;">';
  html += '<p style="margin:0 0 0.5em;font-size:12px;color:#888;font-weight:bold;">参考文献</p>';
  for (const [num, text] of sorted) {
    const linkedText = text.replace(/(https?:\/\/[^\s,)>]+)/g, '<i>$1</i>');
    html += `<p style="margin:2px 0;display:flex;font-size:10px;color:#999;line-height:1.4"><span class="footnote-num" style="display:inline;width:10%;">[${num}]</span><span class="footnote-txt" style="display:inline;width:90%;word-wrap:break-word;word-break:break-all;">${linkedText}</span></p>`;
  }
  html += '</section>';
  _pendingFootnotes = null;
  return html;
}

async function processInlineImages(html, mdDir, accessToken) {
  const imgRegex = /<img\s+[^>]*src="([^"]+\.(png|jpg|jpeg|gif|webp))"[^>]*>/gi;
  let result = html;
  for (const match of [...html.matchAll(imgRegex)]) {
    const src = match[1];
    if (src.startsWith("http")) continue;
    const localPath = path.resolve(mdDir, src);
    if (!fs.existsSync(localPath)) {
      console.log(`⚠️  Image not found: ${src}`);
      continue;
    }
    console.log(`📤 Uploading ${src}...`);
    const wxUrl = await uploadInlineImage(localPath, accessToken);
    result = result.replaceAll(src, wxUrl);
  }
  return result;
}

// === Post-processing: dark-mode-friendly starry theme ===
// Strategy: NO background colors (WeChat dark mode inverts them into ugly gray blocks)
// Use borders, text colors, and subtle decorations only
const S = {
  navy:      "#0f1b35",
  purple:    "#5b4dc7",   // mid-range purple, readable in both modes
  gold:      "#c9952c",   // muted gold, not too bright
  text:      "#2b2b3a",
  textLight: "#555568",
  accent:    "#6c5ce7",   // for strong emphasis
};

function postProcess(html) {
  let e = html;

  // --- Structural fixes ---
  // Blockquote: convert \n to <br/> inside <p> within blockquotes
  e = e.replace(/<blockquote[\s\S]*?<\/blockquote>/g, (bq) => {
    return bq.replace(/<p[^>]*>([\s\S]*?)<\/p>/g, (match, inner) => {
      return match.replace(inner, inner.replace(/\n/g, '<br/>'));
    });
  });

  // Convert remaining **text** to <strong>
  e = e.replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>');

  // --- Dark-mode-safe color overrides ---

  // H2: left border only, NO background
  e = e.replace(
    /(<h2\s+style=")([^"]*)(">)/g,
    `$1margin:1.5em 0 0.8em;font-size:1.15em;font-weight:bold;padding:8px 0 8px 14px;border-left:4px solid ${S.gold};border-bottom:none;background:none;color:${S.navy};text-align:left;$3`
  );

  // Strong: accent color
  e = e.replace(
    /(<strong\s+style=")([^"]*)(">)/g,
    `$1color:${S.accent};font-weight:700;$3`
  );
  e = e.replace(/<strong>/g, `<strong style="color:${S.accent};font-weight:700;">`);

  // Blockquote: left border only, NO background
  e = e.replace(
    /(<blockquote\s+style=")([^"]*)(">)/g,
    `$1border-left:3px solid ${S.purple};margin:1.5em 0;padding:12px 18px;background:none;font-style:normal;color:${S.textLight};font-size:15px;line-height:1.8;$3`
  );

  // Paragraphs
  e = e.replace(
    /(<p\s+style=")([^"]*)(">)/g,
    `$1margin:0.9em 0;line-height:1.85;font-size:16px;color:${S.text};letter-spacing:0.3px;$3`
  );

  // Table th: minimal, no background, subtle bottom border
  e = e.replace(
    /(<th\s+style=")([^"]*)(">)/g,
    `$1font-size:0.85em;padding:10px 12px;line-height:22px;color:${S.accent};border:none;border-bottom:2px solid ${S.accent};font-weight:bold;background:none;vertical-align:top;$3`
  );

  // Table td: very subtle borders
  e = e.replace(
    /(<td\s+style=")([^"]*)(">)/g,
    `$1font-size:0.85em;padding:10px 12px;line-height:22px;color:${S.textLight};border:none;border-bottom:1px solid rgba(0,0,0,0.06);vertical-align:top;$3`
  );

  // Images: subtle shadow
  e = e.replace(
    /(<img[^>]*style=")([^"]*)(">)/g,
    '$1$2border-radius:6px;box-shadow:0 2px 8px rgba(0,0,0,0.1);$3'
  );

  // Li
  e = e.replace(
    /(<li\s+style=")([^"]*)(">)/g,
    `$1$2color:${S.text};$3`
  );

  // HR: thin separator, less bottom margin
  e = e.replace(/<hr[^>]*\/?>/g,
    `<hr style="border:none;border-top:1px dashed #ddd;margin:2em 0 0.8em;">`);

  // === Signature: left-aligned, normal italic (like blog) ===
  e = e.replace(
    /(<hr[^>]*>[\s\S]*?<p\s+style=")([^"]*)(">\s*<em>)/g,
    '$1font-size:14px;color:#888;margin:0.3em 0 0;text-align:left;$3'
  );

  // === Footnotes: own dashed separator, compact, faded, no heading ===
  e = e.replace(
    /<section id="footnotes">/g,
    `<section id="footnotes" style="margin-top:2em;padding-top:1em;border-top:1px dashed #ddd;">`
  );
  // Remove wenyan-md auto-generated "引用链接" section entirely (heading + first footnotes block).
  // We build our own footnotes via buildFootnotesHtml(), so the auto-generated one is redundant.
  e = e.replace(
    /<h3[^>]*>引用链接<\/h3>/g,
    ''
  );
  // Remove the FIRST auto-generated footnotes section (wenyan-md's inline-link references).
  // Our manually built section (from [^N] definitions) is appended later and should be kept.
  e = e.replace(
    /<section id="footnotes"[^>]*>[\s\S]*?<\/section>/,
    ''
  );
  // Remove wenyan-md auto-injected superscript footnote numbers from inline links
  // (e.g. <sup class="footnote" ...>[2]</sup>) — we use our own [^N] numbering
  e = e.replace(/<sup class="footnote"[^>]*>\[\d+\]<\/sup>/g, '');
  // Style remaining footnotes sections (our custom ones): very small and faded
  e = e.replace(
    /<section id="footnotes"[^>]*>([\s\S]*?)(<\/section>)/g,
    (match) => {
      return match.replace(/<p\s+style="[^"]*"/g,
        '<p style="margin:2px 0;display:flex;font-size:10px;color:#ccc;line-height:1.4"');
    }
  );

  return e;
}

// === Main ===
async function main() {
  const { values } = parseArgs({
    options: {
      file: { type: "string", short: "f", multiple: true },
      cover: { type: "string", short: "c", multiple: true },
      title: { type: "string", short: "t", multiple: true },
      url: { type: "string", short: "u", multiple: true },
      author: { type: "string", short: "a", default: "张昊辰" },
      "dry-run": { type: "boolean", default: false },
    }
  });

  const files = values.file || [];
  if (files.length === 0) {
    console.error("Usage: node publish.mjs -f <file1.md> [-f <file2.md>] [-c cover.png] [-t title] [-u url]");
    console.error("  Multiple -f flags for multi-article draft (微信多图文)");
    process.exit(1);
  }

  const titles = values.title || [];
  const covers = values.cover || [];
  const urls = values.url || [];

  const accessToken = await getAccessToken();
  const articles = [];

  for (let i = 0; i < files.length; i++) {
    const mdPath = path.resolve(files[i]);
    const mdDir = path.dirname(mdPath);
    const markdown = fs.readFileSync(mdPath, "utf-8");

    console.log(`\n📄 [${i + 1}/${files.length}] Reading ${files[i]}...`);

    // Extract frontmatter (now includes image)
    const { title: fmTitle, image: fmImage, body: rawBody } = extractFrontmatter(markdown);
    const body = preprocessMarkdown(rawBody);
    const title = titles[i] || fmTitle || body.match(/^#\s+(.+)/m)?.[1] || "Untitled";

    // Render with wenyan-md
    const { content: renderedHtml } = await renderStyledContent(body, {
      theme: "default",
      lineNumbers: false,
    });

    // Post-process
    let html = postProcess(renderedHtml);

    // Append footnotes section (from [^N] definitions extracted during preprocessing)
    html += buildFootnotesHtml();

    // Upload inline images
    html = await processInlineImages(html, mdDir, accessToken);

    if (values["dry-run"]) {
      const outPath = `/tmp/wechat-preview-${i + 1}.html`;
      fs.writeFileSync(outPath, html);
      console.log(`📝 Dry run: saved to ${outPath}`);
      continue;
    }

    // Resolve cover image
    let coverPath = covers[i] || null;
    if (!coverPath && fmImage) {
      coverPath = fmImage;
    }
    if (!coverPath) {
      const imgMatch = body.match(/!\[.*?\]\((.+?)\)/);
      if (imgMatch) coverPath = imgMatch[1];
    }
    if (!coverPath) throw new Error(`No cover image for article ${i + 1}. Use --cover.`);
    coverPath = path.resolve(mdDir, coverPath);

    console.log(`📸 Uploading cover for "${title}"...`);
    const coverMediaId = await uploadCover(coverPath, accessToken);

    articles.push({
      title,
      author: values.author,
      content: html,
      thumb_media_id: coverMediaId,
      need_open_comment: 1,
      only_fans_can_comment: 0,
      content_source_url: urls[i] || "",
    });

    console.log(`✅ Article ${i + 1} ready: ${title}`);
  }

  if (values["dry-run"]) {
    console.log(`\n📝 Dry run complete. ${files.length} preview(s) saved.`);
    return;
  }

  // Create draft with all articles
  console.log(`\n✍️  Creating draft with ${articles.length} article(s)...`);
  const payload = { articles };

  const res = await fetch(`${WECHAT_API}/draft/add?access_token=${accessToken}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();

  if (data.errcode) throw new Error(`Failed to create draft: ${JSON.stringify(data)}`);

  console.log(`✅ Draft created! media_id: ${data.media_id}`);
  console.log(`   ${articles.length} article(s): ${articles.map(a => a.title).join(" | ")}`);
  console.log(`👉 Go to mp.weixin.qq.com to review and publish.`);
}

main().catch(e => { console.error(`❌ ${e.message}`); process.exit(1); });
