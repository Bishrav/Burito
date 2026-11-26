import { createServer } from 'node:http';
import { Client } from 'eve/client';

const token = process.env.BURITO_BRIDGE_TOKEN;
if (!token) throw new Error('Start the web bridge through Burito.');

const client = new Client({ baseUrl: 'http://127.0.0.1:2000' });
const sessions = new Set();
const server = createServer(async (request, response) => {
  function json(status, value) {
    response.writeHead(status, {'content-type': 'application/json; charset=utf-8'});
    response.end(JSON.stringify(value));
  }

  if (request.headers.authorization !== `Bearer ${token}`) {
    return json(403, {error: 'Burito bridge authorization required.'});
  }
  if (request.method === 'GET' && request.url === '/health') {
    return json(200, {status: 'ready'});
  }
  if (request.method !== 'POST' || request.url !== '/chat') {
    return json(404, {error: 'Unknown bridge route.'});
  }

  const chunks = [];
  let size = 0;
  let input;
  try {
    for await (const chunk of request) {
      size += chunk.length;
      if (size > 20_000) return json(413, {error: 'Message is too large.'});
      chunks.push(chunk);
    }
    input = JSON.parse(Buffer.concat(chunks).toString('utf8'));
  } catch {
    return json(400, {error: 'Invalid JSON chat request.'});
  }
  if (typeof input?.message !== 'string' || !input.message.trim()) {
    return json(400, {error: 'Enter a message.'});
  }
  if (input.sessionId != null && !sessions.has(input.sessionId)) {
    return json(409, {error: 'This chat session is no longer available. Start a new chat.'});
  }

  try {
    const message = input.message.trim();
    let session, delivery;
    if (input.sessionId) {
      session = client.sessions.attach(input.sessionId);
      delivery = await session.send(message);
    } else {
      ({session, delivery} = await client.sessions.create({message}));
      sessions.add(session.id);
      if (sessions.size > 256) sessions.delete(sessions.values().next().value);
    }
    const result = await delivery.result({signal: AbortSignal.timeout(120_000)});
    if (result.status !== 'completed' || !result.reply?.trim()) {
      return json(502, {error: 'The local conversation did not produce a completed reply.'});
    }
    return json(200, {sessionId: session.id, status: result.status, reply: result.reply});
  } catch {
    return json(502, {error: 'The local conversation failed. Check Eve and Ollama availability.'});
  }
});
server.listen(2001, '127.0.0.1', () => console.log('Burito Eve client bridge listening on 127.0.0.1:2001'));
