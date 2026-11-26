import { performance } from 'node:perf_hooks';

export async function streamTurn(client, payload, response, turn) {
  const started = performance.now();
  let firstText, inputTokens, outputTokens, modelStarted, modelSettled, finishReason;
  const parts = new Map();
  const deadline = AbortSignal.timeout(120_000);
  const emit = (event) => {
    if (!response.destroyed) response.write(JSON.stringify(event) + '\n');
  };
  response.writeHead(200, {'content-type': 'application/x-ndjson', 'cache-control': 'no-store'});
  emit({type: 'thinking'});
  try {
    const {session, delivery} = await client.sessions.create({
      message: payload.message,
      clientContext: {
        conversation_reference_data: payload.context,
        communication_preferences: payload.personality,
      },
    }, {signal: deadline});
    turn.session = session;
    if (turn.stopRequested) await cancelTurn(turn);
    for await (const event of delivery.stream({signal: deadline})) {
      switch (event.type) {
        case 'delivery.consumed':
          turn.turnId = event.data.turnId;
          break;
        case 'model.started':
          modelStarted = performance.now();
          break;
        case 'model.settled':
          modelSettled = performance.now();
          finishReason = event.data.finishReason;
          if (event.data.outcome === 'interrupted' && turn.stopRequested) break;
          if (event.data.outcome === 'failed' || event.data.outcome === 'abandoned') {
            emit({type: 'thinking'});
          }
          break;
        case 'usage.recorded':
          inputTokens = (inputTokens ?? 0) + event.data.usage.inputTokens;
          outputTokens = (outputTokens ?? 0) + event.data.usage.outputTokens;
          break;
        case 'content.delta': {
          const {partId, kind, delta} = event.data;
          if (kind) parts.set(partId, kind);
          if (parts.get(partId) !== 'text' || !delta) break;
          firstText ??= performance.now();
          emit({type: 'delta', text: delta});
          break;
        }
        case 'call.started':
          emit({type: 'tool'});
          break;
        case 'interaction.opened':
          emit({type: 'approval'});
          break;
      }
    }
    const result = await delivery.result({signal: deadline});
    const completed = result.status === 'completed' && Boolean(result.reply?.trim());
    const ended = performance.now();
    const modelMs = modelSettled != null && modelStarted != null ? modelSettled - modelStarted : null;
    emit({
      type: 'done', status: completed ? 'completed' : result.status === 'cancelled' ? 'cancelled' : 'failed',
      reply: completed ? result.reply : undefined,
      detail: result.status === 'awaiting-input' ? 'This web session cannot authorize tools or runtime prompts.' : undefined,
      metrics: {
        firstTextMs: firstText == null ? null : Math.round(firstText - started),
        totalMs: Math.round(ended - started),
        inputTokens: inputTokens ?? null, outputTokens: outputTokens ?? null, modelMs,
        tokensPerSecond: outputTokens && modelMs > 0 ? outputTokens * 1000 / modelMs : null,
        finishReason: finishReason ?? null,
      },
    });
    if (result.status === 'awaiting-input') await cancelTurn(turn);
  } catch {
    if (turn.session) await cancelTurn(turn).catch(() => {});
    emit({type: 'done', status: 'failed', detail: 'Eve or Ollama interrupted the reply.'});
  } finally {
    if (turn.session) {
      // The durable transcript is replayed as bounded reference data next turn.
      void turn.session.end({}, {signal: AbortSignal.timeout(2500)}).catch(() => {});
    }
  }
}

export async function cancelTurn(turn) {
  turn.stopRequested = true;
  if (turn.session) {
    const signal = AbortSignal.timeout(5000);
    await turn.session.cancel(turn.turnId ? {turnId: turn.turnId} : {}, {signal});
  }
}
