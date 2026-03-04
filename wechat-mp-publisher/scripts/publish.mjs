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
  if (!match) return { title: null, body: markdown };
  const fm = match[1];
  const titleMatch = fm.match(/^title:\s*["']?(.+?)["']?\s*$/m);
  return {
    title: titleMatch ? titleMatch[1] : null,
    body: markdown.slice(match[0].length)
  };
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

// === Post-processing: starry-night color overlay (structure-safe) ===
const S = {
  navy:      "#0f1b35",
  indigo:    "#1b2a4a",
  purple:    "#2d1b69",
  gold:      "#e8b731",
  goldLight: "#f5d76e",
  goldBg:    "#fdf6e3",
  text:      "#1a1a2e",
  textLight: "#4a4a6a",
  quoteBg:   "#f0eef5",
  tableTh:   "#1b2a4a",
  tableThTx: "#f5d76e",
};

function postProcess(html) {
  let e = html;

  // --- Structural fixes only ---
  // Blockquote dialogue line breaks
  e = e.replace(/(<\/strong>)(\s*)(<strong)/g, '$1<br/>$3');

  // --- Color-only overrides (replace style values, keep structure) ---

  // H2: change colors only (keep text-align:center, font-size, etc.)
  e = e.replace(
    /(<h2\s+style=")([^"]*)(">)/g,
    `$1margin:1.5em 0 0.8em;text-align:left;font-size:1.15em;font-weight:bold;padding:10px 16px;background:linear-gradient(135deg,${S.goldBg},#f5f0fa);border-left:4px solid ${S.gold};border-bottom:none;border-radius:4px;color:${S.navy};$3`
  );

  // Strong: purple accent
  e = e.replace(
    /(<strong\s+style=")([^"]*)(">)/g,
    `$1color:${S.purple};font-weight:700;$3`
  );
  // Strong without style
  e = e.replace(/<strong>/g, `<strong style="color:${S.purple};font-weight:700;">`);

  // Blockquote: purple tint
  e = e.replace(
    /(<blockquote\s+style=")([^"]*)(">)/g,
    `$1background:${S.quoteBg};border-left:3px solid ${S.purple};margin:1.5em 0;padding:12px 18px;border-radius:0 4px 4px 0;font-style:normal;color:${S.textLight};font-size:15px;line-height:1.8;$3`
  );

  // Paragraphs: adjust color
  e = e.replace(
    /(<p\s+style=")([^"]*)(">)/g,
    `$1margin:0.9em 0;line-height:1.85;font-size:16px;color:${S.text};letter-spacing:0.3px;$3`
  );

  // Table th: dark header
  e = e.replace(
    /(<th\s+style=")([^"]*)(">)/g,
    `$1font-size:0.85em;padding:10px 12px;line-height:22px;color:${S.tableThTx};border:1px solid ${S.indigo};font-weight:bold;background:${S.tableTh};vertical-align:top;$3`
  );

  // Table td: subtle style
  e = e.replace(
    /(<td\s+style=")([^"]*)(">)/g,
    `$1font-size:0.85em;padding:10px 12px;line-height:22px;color:${S.textLight};border:1px solid #d0d0e0;vertical-align:top;$3`
  );

  // Images: add shadow (keep existing style)
  e = e.replace(
    /(<img[^>]*style=")([^"]*)(">)/g,
    '$1$2border-radius:6px;box-shadow:0 2px 12px rgba(15,27,53,0.12);$3'
  );

  // Li: text color
  e = e.replace(
    /(<li\s+style=")([^"]*)(">)/g,
    `$1$2color:${S.text};$3`
  );

  // HR: gradient divider
  e = e.replace(/<hr[^>]*\/?>/g,
    `<section style="text-align:center;margin:2em 0;"><section style="display:inline-block;width:40%;height:1px;background:linear-gradient(to right,transparent,${S.gold},transparent);"></section></section>`);

  return e;
}

// === Main ===
async function main() {
  const { values } = parseArgs({
    options: {
      file: { type: "string", short: "f" },
      cover: { type: "string", short: "c" },
      title: { type: "string", short: "t" },
      url: { type: "string", short: "u", default: "" },
      author: { type: "string", short: "a", default: "张昊辰(Astralor)" },
      "dry-run": { type: "boolean", default: false },
    }
  });

  if (!values.file) {
    console.error("Usage: node publish.mjs -f <markdown-file> [-c cover.png] [-u url] [-t title]");
    process.exit(1);
  }

  const mdPath = path.resolve(values.file);
  const mdDir = path.dirname(mdPath);
  const markdown = fs.readFileSync(mdPath, "utf-8");

  console.log(`📄 Reading ${values.file}...`);

  // Extract frontmatter
  const { title: fmTitle, body } = extractFrontmatter(markdown);
  const title = values.title || fmTitle || body.match(/^#\s+(.+)/m)?.[1] || "Untitled";

  // Render with wenyan-md
  const { content: renderedHtml } = await renderStyledContent(body, {
    theme: "default",
    lineNumbers: false,
  });

  // Post-process
  let html = postProcess(renderedHtml);

  // Get access token
  const accessToken = await getAccessToken();

  // Upload inline images
  html = await processInlineImages(html, mdDir, accessToken);

  if (values["dry-run"]) {
    const outPath = "/tmp/wechat-preview.html";
    fs.writeFileSync(outPath, html);
    console.log(`📝 Dry run: saved to ${outPath}`);
    return;
  }

  // Upload cover
  let coverPath = values.cover;
  if (!coverPath) {
    const imgMatch = body.match(/!\[.*?\]\((.+?)\)/);
    if (imgMatch) coverPath = path.resolve(mdDir, imgMatch[1]);
  }
  if (!coverPath) throw new Error("No cover image. Use --cover.");
  coverPath = path.resolve(mdDir, coverPath);

  console.log(`📸 Uploading cover...`);
  const coverMediaId = await uploadCover(coverPath, accessToken);

  // Create draft
  console.log(`✍️  Creating draft: ${title}...`);
  const payload = {
    articles: [{
      title,
      author: values.author,
      content: html,
      thumb_media_id: coverMediaId,
      need_open_comment: 1,
      only_fans_can_comment: 0,
      content_source_url: values.url || "",
    }]
  };

  const res = await fetch(`${WECHAT_API}/draft/add?access_token=${accessToken}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();

  if (data.errcode) throw new Error(`Failed to create draft: ${JSON.stringify(data)}`);

  console.log(`✅ Draft created! media_id: ${data.media_id}`);
  console.log(`👉 Go to mp.weixin.qq.com to review and publish.`);
}

main().catch(e => { console.error(`❌ ${e.message}`); process.exit(1); });
