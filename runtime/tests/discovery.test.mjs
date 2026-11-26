import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';

test('installed eve starts with no default or eagerly registered tools', () => {
  const result = spawnSync('eve', ['info', '--json'], { encoding: 'utf8',
    env: { ...process.env, EVE_TELEMETRY_DISABLED: '1', EVE_TRACES_CONTENT: 'off' } });
  assert.equal(result.status, 0, result.stderr);
  const info = JSON.parse(result.stdout);
  assert.equal(info.status, 'ready');
  assert.equal(info.diagnostics.errors, 0);
  // Eve resolves dynamic PC tools at the first model call.
  assert.deepEqual(info.tools, []);
  assert.deepEqual(info.subagents, []);
  assert.deepEqual(info.schedules, []);
});
