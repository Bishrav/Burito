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
    response.writeHead(result.status === 'failed' ? 502 : 200, { 'content-type': 'application/json; charset=utf-8' });
    response.end(JSON.stringify({ sessionId: session.id, status: result.status, reply: result.reply ?? '', error: result.error?.message }));
  } catch (error) {
    response.writeHead(502, { 'content-type': 'application/json; charset=utf-8' });
    response.end(JSON.stringify({ error: error instanceof Error ? error.message : String(error) }));
  }
});
server.listen(2001, '127.0.0.1', () => console.log('Burito Eve client bridge listening on 127.0.0.1:2001'));
