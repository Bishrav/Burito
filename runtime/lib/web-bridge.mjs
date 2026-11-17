import { createServer } from 'node:http';
import { Client } from 'eve/client';

const client = new Client({ baseUrl: 'http://127.0.0.1:2000' });
const server = createServer(async (request, response) => {
  if (request.method !== 'POST' || request.url !== '/chat') {
    response.writeHead(404).end();
    return;
  }
  let raw = '';
  for await (const chunk of request) {
    raw += chunk;
    if (raw.length > 20_000) {
      response.writeHead(413).end(JSON.stringify({ error: 'Message is too large.' }));
      return;
    }
  }
  try {
    const input = JSON.parse(raw);
    if (typeof input.message !== 'string' || !input.message.trim()) throw new Error('Enter a message.');
    const { session, delivery } = input.sessionId
      ? { session: client.sessions.attach(input.sessionId), delivery: null }
      : await client.sessions.create({ message: input.message.trim() });
    const result = delivery
      ? await delivery.result()
      : await (await session.send(input.message.trim())).result();
    const snapshot = await session.snapshot();
    const modelUsage = snapshot.events
      .filter((event) => event.type === 'usage.recorded' && event.data?.kind === 'model')
      .map((event) => event.data.usage)
      .filter((usage) => usage && Number.isFinite(usage.inputTokens) && Number.isFinite(usage.outputTokens));
    const totals = modelUsage.reduce((sum, usage) => ({
      inputTokens: sum.inputTokens + usage.inputTokens,
      outputTokens: sum.outputTokens + usage.outputTokens,
    }), { inputTokens: 0, outputTokens: 0 });
    const currentTurnId = [...snapshot.events].reverse()
      .find((event) => event.type === 'turn.started')?.data?.turnId;
    const latestTurnUsage = snapshot.events
      .filter((event) => event.type === 'usage.recorded' && event.data?.kind === 'model' &&
        event.scope?.turnId === currentTurnId)
      .map((event) => event.data.usage)
      .filter((usage) => usage && Number.isFinite(usage.inputTokens) && Number.isFinite(usage.outputTokens))
      .at(-1);
    const contextLimit = Number.parseInt(process.env.BURITO_CONTEXT_TOKENS ?? '', 10);
    const requestTokens = latestTurnUsage
      ? latestTurnUsage.inputTokens + latestTurnUsage.outputTokens
      : null;
    response.writeHead(result.status === 'failed' ? 502 : 200, { 'content-type': 'application/json; charset=utf-8' });
    response.end(JSON.stringify({
      sessionId: session.id,
      status: result.status,
      reply: result.reply ?? '',
      error: result.error?.message,
      tokenUsage: {
        reported: modelUsage.length > 0,
        contextLimit: Number.isFinite(contextLimit) && contextLimit > 0 ? contextLimit : null,
        latestInput: latestTurnUsage?.inputTokens ?? null,
        latestOutput: latestTurnUsage?.outputTokens ?? null,
        latestRequestTokens: requestTokens,
        estimatedContextRemaining: Number.isFinite(contextLimit) && contextLimit > 0 && requestTokens !== null
          ? Math.max(contextLimit - requestTokens, 0)
          : null,
        sessionInput: totals.inputTokens,
        sessionOutput: totals.outputTokens,
        sessionTotal: totals.inputTokens + totals.outputTokens,
      },
    }));
  } catch (error) {
    response.writeHead(502, { 'content-type': 'application/json; charset=utf-8' });
    response.end(JSON.stringify({ error: error instanceof Error ? error.message : String(error) }));
  }
});
server.listen(2001, '127.0.0.1', () => console.log('Burito Eve client bridge listening on 127.0.0.1:2001'));
