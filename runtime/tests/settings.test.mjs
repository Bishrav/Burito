import test from 'node:test';
import assert from 'node:assert/strict';
import { readSettings } from '../lib/settings.mjs';

const base = { BURITO_LOCAL_MODEL: 'synthetic-test-model', BURITO_CONTEXT_TOKENS: '8192' };

test('defaults to literal loopback and excludes personal data', () => {
  const settings = readSettings(base);
  assert.equal(settings.baseURL, 'http://127.0.0.1:11434/v1');
  assert.equal(settings.includePersonal, false);
  assert.equal(settings.lesson, 'home.honesty');
  assert.equal(settings.includeExperiences, false);
  assert.equal(settings.includeAcademy, false);
});

test('cognitive records require explicit scopes', () => {
  const settings = readSettings({ ...base, BURITO_INCLUDE_EXPERIENCES: '1',
    BURITO_INCLUDE_ACADEMY: '1' });
  assert.equal(settings.includeExperiences, true);
  assert.equal(settings.includeAcademy, true);
});

test('does not accept remote endpoints or cloud fallback', () => {
  for (const url of ['https://example.com/v1', 'file:///tmp/test',
    'http://127.0.0.1.evil.example/v1', 'http://user:pass@127.0.0.1/v1']) {
    assert.throws(() => readSettings({ ...base, BURITO_LOCAL_URL: url }));
  }
  assert.throws(() => readSettings({ ...base, BURITO_MODE: 'cloud' }));
});

test('requires explicit model and valid allocated context', () => {
  assert.throws(() => readSettings({ BURITO_CONTEXT_TOKENS: '8192' }));
  for (const size of ['', 'unknown', '4095', '200000', '8192.5']) {
    assert.throws(() => readSettings({ ...base, BURITO_CONTEXT_TOKENS: size }));
  }
});
