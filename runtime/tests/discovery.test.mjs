import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

test('installed eve exposes only explicit PC tools, not default shell/file/web tools', () => {
  // The preceding check:discovery command compiles fresh public CLI output.
  const info = JSON.parse(readFileSync(new URL('../.eve-info.json', import.meta.url), 'utf8'));
  assert.equal(info.status, 'ready');
  assert.equal(info.diagnostics.errors, 0);
  assert.deepEqual([...info.tools].sort(), ['applications', 'files', 'open_application']);
  assert.deepEqual(info.subagents, []);
  assert.deepEqual(info.schedules, []);
});
