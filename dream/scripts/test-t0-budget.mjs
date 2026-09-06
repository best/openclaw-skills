import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { run } from './t0-budget-check.mjs';

function fixture(files, args = []) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'dream-budget-'));
  try {
    for (const [name, body] of Object.entries(files)) fs.writeFileSync(path.join(root, name), body);
    const output = [];
    const exit = run([root, '--json', ...args], text => output.push(text));
    return { exit, out: JSON.parse(output.join('')) };
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
}
test('CJK characters and bytes remain distinct', () => {
  const r = fixture({ 'MEMORY.md': '汉'.repeat(100) });
  assert.equal(r.exit, 0);
  assert.equal(r.out.chars, 100);
  assert.equal(r.out.bytes, 300);
});
test('local policy overflow is not claimed to be native truncation', () => {
  const r = fixture({ 'MEMORY.md': 'a'.repeat(15000) });
  assert.equal(r.exit, 20);
  assert.match(r.out.budgetScope, /local-curation/);
  assert.equal(r.out.bootstrapReference.files.find(f => f.name === 'MEMORY.md').exceedsReferenceLimit, false);
});
test('USER independent cap is enforced even with small MEMORY', () => {
  const r = fixture({ 'MEMORY.md': 'stable', 'USER.md': 'a'.repeat(4001) });
  assert.equal(r.exit, 10);
  assert.equal(r.out.ok, false);
});
test('ordinary root Markdown is not inventoried as bootstrap', () => {
  const r = fixture({ 'MEMORY.md': 'stable', 'report.md': 'a'.repeat(100000) });
  assert.equal(r.exit, 0);
  assert.equal(r.out.bootstrapReference.files.some(f => f.name === 'report.md'), false);
  assert.equal(r.out.bootstrapReference.totalInventoryChars, 6);
});
test('caller budget overrides affect reference inventory without claiming discovered config', () => {
  const r = fixture({ 'MEMORY.md': 'stable', 'USER.md': 'a'.repeat(1500) }, ['--bootstrap-max-chars', '1000', '--bootstrap-total-max-chars', '1200']);
  assert.equal(r.exit, 10);
  assert.equal(r.out.bootstrapReference.exceedsTotalReference, true);
  assert.equal(r.out.bootstrapReference.files.find(f => f.name === 'USER.md').referenceLimit, 1000);
});
test('sensitive findings expose rule and line only', () => {
  const r = fixture({ 'MEMORY.md': 'password = synthetic-sensitive-fixture' });
  assert.equal(r.exit, 10);
  assert.equal(r.out.forbiddenHits[0].line, 1);
  assert.equal(JSON.stringify(r.out).includes('synthetic-sensitive-fixture'), false);
});
test('negative storage guardrails are not treated as stored secrets', () => {
  const r = fixture({ 'MEMORY.md': 'Never store a password.\n不要写入密码。' });
  assert.equal(r.exit, 0);
  assert.equal(r.out.forbiddenHits.length, 0);
});
test('missing memory remains a distinct operational failure', () => {
  const r = fixture({});
  assert.equal(r.exit, 2);
  assert.equal(r.out.ok, false);
});
test('invalid budgets fail without silently adopting a default', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'dream-budget-'));
  try {
    fs.writeFileSync(path.join(root, 'MEMORY.md'), 'stable');
    assert.throws(() => run([root, '--bootstrap-max-chars', 'bad']), /positive safe integer/);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});
