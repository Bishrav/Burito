import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

test('installed eve compiles the conversation agent without action tools', () => {
  // The preceding check:discovery command compiles fresh public CLI output.
  const info = JSON.parse(readFileSync(new URL('../.eve-info.json', import.meta.url), 'utf8'));
  assert.equal(info.status, 'ready');
  assert.equal(info.diagnostics.errors, 0);
  assert.deepEqual(info.tools, []);
  assert.deepEqual(info.subagents, []);
  assert.deepEqual(info.schedules, []);
});
