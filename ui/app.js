const clock = document.querySelector('#clock');
const date = document.querySelector('#date');
const toast = document.querySelector('#toast');
const form = document.querySelector('#composer');
const input = document.querySelector('#message');
const submit = form.querySelector('button');
const conversation = document.querySelector('#conversation');
const status = document.querySelector('#connectionStatus');
const connectionMessage = document.querySelector('#connectionMessage');
const pill = document.querySelector('.connection-card .pill');
const model = document.querySelector('#runtimeModel');
const runtimeSummary = document.querySelector('#runtimeSummary');

let sessionId = null;
let busy = false;
let ready = false;

function tick() {
  const now = new Date();
  clock.textContent = now.toLocaleTimeString([], {hour12: false});
  date.textContent = now.toLocaleDateString([], {
    year: 'numeric', month: 'short', day: '2-digit',
  }).toUpperCase();
}
tick();
setInterval(tick, 1000);

document.querySelectorAll('[data-nav]').forEach(button => button.addEventListener('click', () => {
  const target = button.dataset.nav;
  const section = document.getElementById(target);
  if (section) {
    section.scrollIntoView({behavior: 'smooth', block: 'start'});
    document.querySelectorAll('.nav-item').forEach(item => {
      item.classList.toggle('active', item.dataset.nav === target);
    });
  } else {
    toast.textContent = `${target.toUpperCase()} view is planned.`;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2400);
  }
}));

function addMessage(role, text) {
  const row = document.createElement('div');
  row.className = `chat-message ${role}`;
  const who = document.createElement('b');
  who.textContent = role === 'user' ? 'YOU' : 'BURITO';
  const body = document.createElement('p');
  body.textContent = text;
  row.append(who, body);
  conversation.append(row);
  row.scrollIntoView({block: 'nearest'});
  return body;
}

function updateComposer() {
  input.disabled = !ready;
  submit.disabled = !ready || busy;
}

async function checkHealth() {
  if (busy) return;
  let message;
  try {
    const response = await fetch('/api/status', {signal: AbortSignal.timeout(8000)});
    const health = await response.json();
    ready = response.ok && health.status === 'ready';
    model.textContent = health.model || 'Unknown';
    if (ready) message = `Connected to Eve and ${health.model} on this computer.`;
    else if (!health.ollama) message = 'The local Ollama service is unavailable.';
    else if (!health.modelInstalled) message = `The model ${health.model} is unavailable in Ollama.`;
    else message = 'The local Eve runtime or chat bridge is not ready.';
  } catch {
    ready = false;
    model.textContent = 'Unknown';
    message = 'The Burito web server is unavailable.';
  }
  if (!busy) {
    status.textContent = ready ? 'LOCAL RUNTIME READY' : 'RUNTIME UNAVAILABLE';
    connectionMessage.textContent = message;
    runtimeSummary.textContent = message;
    pill.classList.toggle('neutral', ready);
    pill.classList.toggle('amber', !ready);
    pill.textContent = ready ? 'LOCAL READY' : 'UNAVAILABLE';
  }
  updateComposer();
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  const text = input.value.trim();
  if (!ready || !text || busy) return;
  busy = true;
  updateComposer();
  input.value = '';
  addMessage('user', text);
  const reply = addMessage('assistant', 'Thinking…');
  status.textContent = 'BURITO IS RESPONDING';
  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: text, sessionId}),
      signal: AbortSignal.timeout(130000),
    });
    const result = await response.json();
    if (response.status === 409) sessionId = null;
    if (!response.ok || result.status !== 'completed') {
      throw Error(result.error || `Local chat returned ${response.status}`);
    }
    sessionId = result.sessionId;
    reply.textContent = result.reply;
    if (result.notificationAccepted === false) {
      toast.textContent = 'The desktop notification could not be delivered.';
      toast.classList.add('show');
      setTimeout(() => toast.classList.remove('show'), 2400);
    }
    status.textContent = 'LOCAL RUNTIME READY';
  } catch (error) {
    reply.textContent = `Could not complete the local chat turn: ${error.message}`;
    status.textContent = 'CHAT ERROR';
  } finally {
    busy = false;
    updateComposer();
    input.focus();
  }
});

updateComposer();
checkHealth();
setInterval(checkHealth, 5000);
