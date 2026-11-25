import test from 'node:test';
import assert from 'node:assert/strict';
import { resolveOpenApplication } from '../agent/tools/open_application.ts';
import { hostAccess } from '../lib/host-access.mjs';

test('application tool requires approval before execution', async () => {
  assert.equal(resolveOpenApplication({}), null);
  assert.equal(resolveOpenApplication({ BURITO_PC_ACCESS: '0' }), null);
  const openApplication = resolveOpenApplication({ BURITO_PC_ACCESS: '1' });
  assert.equal(typeof openApplication.approval, 'function');
  const decision = await openApplication.approval({ toolInput: { app_id: 'test:demo.desktop' } });
  assert.equal(decision, 'user-approval');
});

test('disabled PC access and cloud mode stop before the host bridge', async () => {
  const previous = { ...process.env };
  try {
    Object.assign(process.env, {
      BURITO_MODE: 'local', BURITO_LOCAL_MODEL: 'synthetic-model',
      BURITO_CONTEXT_TOKENS: '8192', BURITO_PC_ACCESS: '0',
    });
    await assert.rejects(hostAccess({ action: 'read', path: '/etc/passwd' }), /disabled/);
    process.env.BURITO_MODE = 'cloud';
    process.env.BURITO_PC_ACCESS = '1';
    await assert.rejects(hostAccess({ action: 'read', path: '/etc/passwd' }), /Cloud routing/);
  } finally {
    for (const key of Object.keys(process.env)) if (!(key in previous)) delete process.env[key];
    Object.assign(process.env, previous);
  }
});
