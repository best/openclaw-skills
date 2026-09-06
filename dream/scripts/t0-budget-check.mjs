#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { parseArgs } from 'node:util';
import { fileURLToPath } from 'node:url';

const POLICY_LIMIT = 12000;
const TARGET_MIN = 9000;
const TARGET_MAX = 10500;
const WARN = 11000;
const CRITICAL = 11800;
const BOOTSTRAP_NAMES = ['AGENTS.md', 'SOUL.md', 'IDENTITY.md', 'USER.md', 'BOOTSTRAP.md', 'MEMORY.md'];

const forbidden = [
  { id: 'maintenance_trace', re: /(已压缩|旧版备份|本次压缩|压缩前|迁移前|review 过程|归档文件|precompact|archive\/MEMORY|reference\.bak|state\/backups)/i },
  { id: 'secret_or_token_hint', re: /(API[_ -]?KEY|api key|token\s*(?:[:=]|文件|路径)|password|密码|secret|openid|ou_[0-9a-f]{8,})/i },
  { id: 'precise_runtime_id', re: /(Cron Job ID|job id|channel id|ID[:：]\s*[0-9a-f-]{12,}|[0-9]{15,})/i },
  { id: 'dynamic_runtime_state', re: /(当前默认模型|当前模型|具体 cron 模型|provider 当前状态|lastStatus|lastRunAtMs|consecutiveErrors)/i },
];

function positiveInteger(value, fallback) {
  if (value === undefined) return fallback;
  if (!/^[1-9][0-9]*$/.test(value) || !Number.isSafeInteger(Number(value))) throw new Error('Budget must be a positive safe integer');
  return Number(value);
}

function policyStatus(chars) {
  if (chars > POLICY_LIMIT) return 'over_limit';
  if (chars > CRITICAL) return 'critical';
  if (chars > WARN) return 'needs_compaction';
  if (chars > TARGET_MAX) return 'watch';
  return chars >= TARGET_MIN ? 'ok_target' : 'ok_small';
}

function metadata(file, text) {
  return { path: file, chars: text.length, bytes: Buffer.byteLength(text, 'utf8'), lines: text.split(/\r?\n/).length };
}

function scanMemory(file, text) {
  const hits = [];
  for (const [index, line] of text.split(/\r?\n/).entries()) {
    if (/(不写|不把|不要|禁止|实时查|不进 T0|不在 T0|不得写入|避免写入|\bnever\b|\bdo not\b)/i.test(line)) continue;
    for (const rule of forbidden) {
      // Findings identify location and rule without exposing credential-like text.
      if (rule.re.test(line)) hits.push({ line: index + 1, rule: rule.id });
    }
  }
  return {
    ...metadata(file, text),
    limit: POLICY_LIMIT,
    budgetScope: 'local-curation-policy-not-runtime-injection',
    target: [TARGET_MIN, TARGET_MAX],
    warn: WARN,
    critical: CRITICAL,
    status: policyStatus(text.length),
    forbiddenHits: hits,
  };
}

export function run(args = process.argv.slice(2), write = console.log) {
  const { values, positionals } = parseArgs({
    args,
    allowPositionals: true,
    options: { json: { type: 'boolean' }, 'bootstrap-max-chars': { type: 'string' }, 'bootstrap-total-max-chars': { type: 'string' } },
  });
  if (positionals.length > 1) throw new Error('Expected one workspace directory');
  const root = path.resolve(positionals[0] || process.cwd());
  const maxFileChars = positiveInteger(values['bootstrap-max-chars'], 20000);
  const maxTotalChars = positiveInteger(values['bootstrap-total-max-chars'], 60000);
  const memoryPath = path.join(root, 'MEMORY.md');
  let memoryText;
  try {
    memoryText = fs.readFileSync(memoryPath, 'utf8');
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
    write(JSON.stringify({ ok: false, error: 'MEMORY.md not found', path: memoryPath }));
    return 2;
  }

  const result = scanMemory(memoryPath, memoryText);
  const files = BOOTSTRAP_NAMES.map(name => {
    const file = path.join(root, name);
    let text;
    try {
      text = name === 'MEMORY.md' ? memoryText : fs.readFileSync(file, 'utf8');
    } catch (error) {
      if (error.code === 'ENOENT') return { name, path: file, missing: true };
      throw error;
    }
    const referenceLimit = name === 'USER.md' ? Math.min(4000, maxFileChars) : maxFileChars;
    return { name, ...metadata(file, text), referenceLimit, exceedsReferenceLimit: text.length > referenceLimit };
  });
  const totalInventoryChars = files.reduce((n, file) => n + (file.chars || 0), 0);
  result.bootstrapReference = {
    scope: 'standard-file-inventory-not-actual-model-context',
    source: values['bootstrap-max-chars'] || values['bootstrap-total-max-chars'] ? 'caller-supplied-with-documented-defaults' : 'documented-defaults-not-discovered',
    maxFileChars,
    maxTotalChars,
    totalInventoryChars,
    exceedsTotalReference: totalInventoryChars > maxTotalChars,
    files,
  };
  const userOverflow = files.some(file => file.name === 'USER.md' && file.exceedsReferenceLimit);
  result.ok = result.chars <= WARN && result.forbiddenHits.length === 0 && !userOverflow;
  if (values.json) write(JSON.stringify(result, null, 2));
  else {
    write(result.path + ': ' + result.chars + '/' + result.limit + ' local-policy chars, ' + result.status);
    write('Bootstrap inventory only: ' + totalInventoryChars + ' chars; runtime injection must be verified separately.');
    if (userOverflow) write('USER.md exceeds its reference budget.');
    for (const hit of result.forbiddenHits) write('L' + hit.line + ' [' + hit.rule + ']');
  }
  return result.chars > POLICY_LIMIT ? 20 : result.ok ? 0 : 10;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    process.exitCode = run();
  } catch {
    console.error(JSON.stringify({ ok: false, error: 'Budget check failed: verify arguments and file readability' }));
    process.exitCode = 2;
  }
}
