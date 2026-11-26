import assert from 'node:assert/strict';
import test from 'node:test';
import { cancelTurn, streamTurn } from '../lib/stream-turn.mjs';

test('forwards visible deltas before completion and keeps reasoning private', async () => {
  const events = [];
  const response = {
    writeHead() {},
    write: line => events.push(JSON.parse(line)),
    end() {},
  };
  const session = {end: async () => {}, cancel: async () => {}};
  let resolveStream;
  const barrier = new Promise(resolve => { resolveStream = resolve; });
  let visible;
  const observed = new Promise(resolve => { visible = resolve; });
  const delivery = {
    async *stream() {
      yield {type: 'content.delta', data: {partId: 'r', kind: 'reasoning', delta: 'private'}};
      yield {type: 'content.delta', data: {partId: 'r', delta: ' reasoning'}};
      yield {type: 'content.delta', data: {partId: 'a', kind: 'text', delta: 'first'}};
      visible();
      await barrier;
      yield {type: 'content.delta', data: {partId: 'a', delta: ' text'}};
    },
    result: async () => ({status: 'completed', reply: 'first text'}),
  };
  const client = {sessions: {create: async () => ({session, delivery})}};
  const turn = streamTurn(client, {message: 'synthetic'}, response, {});
  await observed;
  assert.deepEqual(events, [{type: 'thinking'}, {type: 'delta', text: 'first'}]);
  resolveStream();
  await turn;
  assert.equal(events.at(-1).reply, 'first text');
  assert.equal(events.at(-1).status, 'completed');
});

test('stop targets the actual Eve turn', async () => {
  const calls = [];
  const turn = {turnId: 'synthetic', session: {cancel: async argument => calls.push(argument)}};
  await cancelTurn(turn);
  assert.deepEqual(calls, [{turnId: 'synthetic'}]);
  assert.equal(turn.stopRequested, true);
});
