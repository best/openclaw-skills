#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const root = process.argv[2] || process.cwd();
const asJson = process.argv.includes('--json');
const memoryPath = path.join(root, 'MEMORY.md');

const LIMIT = 12000;
const TARGET_MIN = 9000;
const TARGET_MAX = 10500;
const WARN = 11000;
const CRITICAL = 11800;

const forbidden = [
  { id: 'maintenance_trace', re: /(已压缩|旧版备份|本次压缩|压缩前|迁移前|review 过程|归档文件|precompact|archive\/MEMORY|reference\.bak|state\/backups)/i },
  { id: 'secret_or_token_hint', re: /(API[_ -]?KEY|api key|token\s*(?:[:=]|文件|路径)|password|密码|secret|openid|ou_[0-9a-f]{8,})/i },
  { id: 'precise_runtime_id', re: /(Cron Job ID|job id|channel id|ID[:：]\s*[0-9a-f-]{12,}|[0-9]{15,})/i },
  { id: 'dynamic_runtime_state', re: /(当前默认模型|当前模型|具体 cron 模型|provider 当前状态|lastStatus|lastRunAtMs|consecutiveErrors)/i },
];

function status(chars) {
  if (chars > LIMIT) return 'over_limit';
  if (chars > CRITICAL) return 'critical';
  if (chars > WARN) return 'needs_compaction';
  if (chars > TARGET_MAX) return 'watch';
  if (chars >= TARGET_MIN) return 'ok_target';
  return 'ok_small';
}

function isGuardrailLine(line) {
  return /(不写|不把|不要|禁止|实时查|不进 T0|不在 T0|不得写入|避免写入)/i.test(line);
}

function scanFile(file) {
  const text = fs.readFileSync(file, 'utf8');
  const lines = text.split(/\r?\n/);
  const hits = [];

  for (const [idx, line] of lines.entries()) {
    // Lines that explicitly say "do not store X" are useful guardrails, not violations.
    if (isGuardrailLine(line)) continue;
    for (const rule of forbidden) {
      if (rule.re.test(line)) {
        hits.push({ line: idx + 1, rule: rule.id, text: line.slice(0, 220) });
      }
    }
  }

  return {
    path: file,
    chars: text.length,
    bytes: Buffer.byteLength(text, 'utf8'),
    lines: lines.length,
    limit: LIMIT,
    target: [TARGET_MIN, TARGET_MAX],
    warn: WARN,
    critical: CRITICAL,
    status: status(text.length),
    forbiddenHits: hits,
  };
}

if (!fs.existsSync(memoryPath)) {
  const out = { ok: false, error: `MEMORY.md not found: ${memoryPath}` };
  console.log(JSON.stringify(out, null, 2));
  process.exit(2);
}

const result = scanFile(memoryPath);
result.ok = result.chars <= WARN && result.forbiddenHits.length === 0;

if (asJson) {
  console.log(JSON.stringify(result, null, 2));
} else {
  console.log(`${result.path}: ${result.chars}/${result.limit} chars, ${result.lines} lines, ${result.status}`);
  if (result.forbiddenHits.length) {
    console.log('forbidden hits:');
    for (const hit of result.forbiddenHits) console.log(`  L${hit.line} [${hit.rule}] ${hit.text}`);
  }
}

process.exit(result.chars > LIMIT ? 20 : result.chars > WARN || result.forbiddenHits.length ? 10 : 0);
