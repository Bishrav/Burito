import { copyButton, renderMarkdown } from './markdown.js';

const byId = id => document.getElementById(id);
const composer = byId('composer');
const input = byId('message');
const conversation = byId('conversation');
const search = byId('chat-search');
const history = byId('chat-history');
const status = byId('connectionStatus');
const metrics = byId('turn-metrics');
const stop = byId('stop-reply');
const retry = byId('retry-reply');
let selected = null;
let current;
let mediaRecorder;
let ready = false;
let voiceReady = false;
let busy = false;
let stopped = false;
let activeRequest;
let pending;
let voiceStream;
let voiceChunks = [];
let voiceTimer;
let voiceBusy = false;
let voiceStarting = false;
let cancelVoiceStart = false;
let discardVoice = false;
let reconcileRequest;
let historyOffset = 0;
let historyVersion = 0;
let unavailable = 'Checking local connection';

function report(message) {
  byId('connectionMessage').textContent = message;
}
function localSelection(id) {
  try {
    if (id) localStorage.setItem('burito-selected', id);
    else localStorage.removeItem('burito-selected');
  } catch {
    // Conversation history remains accessible when browser storage is disabled.
  }
}
function getSelection() {
  try { return localStorage.getItem('burito-selected'); } catch { return null; }
}
function requestId() {
  return crypto.randomUUID().replaceAll('-', '');
}
function lastTurn() {
  return current?.turns.at(-1);
}
function updateControls() {
  const running = lastTurn()?.status === 'running';
  input.disabled = !ready || busy || voiceStarting || voiceBusy || running;
  byId('send-message').disabled = input.disabled;
  byId('record-voice').disabled = !ready || !voiceReady || busy || voiceStarting || voiceBusy;
  byId('voice-language').disabled = voiceStarting || voiceBusy || Boolean(mediaRecorder);
  stop.disabled = stopped || (!running && !activeRequest);
  retry.disabled = !ready || busy || running || !(pending || ['failed', 'cancelled', 'interrupted'].includes(lastTurn()?.status));
  for (const id of ['new-chat', 'rename-chat', 'delete-chat', 'older-turns']) {
    byId(id).disabled = busy || (id !== 'new-chat' && !selected);
  }
}
function button(label, handler) {
  const control = document.createElement('button');
  control.type = 'button';
  control.textContent = label;
  control.addEventListener('click', handler);
  return control;
}

async function api(path, method = 'GET', data) {
  const options = {method, signal: AbortSignal.timeout(10000)};
  if (data !== undefined) {
    options.headers = {'Content-Type': 'application/json'};
    options.body = JSON.stringify(data);
  }
  const response = await fetch(path, options);
  const result = await response.json();
  if (!response.ok) throw Error(result.error || `HTTP ${response.status}`);
  return result;
}

function appendMessage(role, text, live = false) {
  const row = document.createElement('div');
  row.className = `chat-message ${role}`;
  const label = document.createElement('b');
  label.textContent = role === 'user' ? 'YOU' : 'BURITO';
  const body = document.createElement(role === 'user' || live ? 'p' : 'div');
  if (role === 'user' || live) body.textContent = text;
  else {
    renderMarkdown(body, text);
    if (text) body.append(copyButton('Copy response', text));
  }
  row.append(label, body);
  conversation.append(row);
  return body;
}
function displayMetrics(value) {
  if (!value) {
    metrics.textContent = '';
    return;
  }
  const measures = [];
  if (value.firstTextMs != null) measures.push(`First text ${value.firstTextMs} ms`);
  if (value.totalMs != null) measures.push(`Total ${value.totalMs} ms`);
  if (value.tokensPerSecond != null) measures.push(`${value.tokensPerSecond.toFixed(1)} model tokens/s`);
  if (value.inputTokens != null) measures.push(`${value.inputTokens} input tokens`);
  metrics.textContent = measures.join(' · ');
}
function displayChat() {
  byId('chat-title').textContent = current?.title || 'Conversations';
  byId('older-turns').hidden = !current?.before;
  conversation.replaceChildren();
  for (const turn of current?.turns ?? []) {
    appendMessage('user', turn.message);
    if (turn.reply) appendMessage('assistant', turn.reply);
    if (turn.status !== 'completed') appendMessage('assistant', {
      running: 'Reply in progress…',
      cancelled: 'Reply stopped.',
      failed: 'Reply failed. Retry when the local runtime is ready.',
      interrupted: 'Reply interrupted by a previous shutdown. Retry to continue.',
    }[turn.status]);
  }
  conversation.scrollTop = conversation.scrollHeight;
  displayMetrics(lastTurn()?.metrics);
  updateControls();
}
async function refreshHistory(append = false) {
  const version = ++historyVersion;
  if (!append) historyOffset = 0;
  const result = await api(`/api/conversations?q=${encodeURIComponent(search.value.trim())}&offset=${historyOffset}`);
  if (version !== historyVersion) return;
  if (!append) history.replaceChildren();
  for (const chat of result.conversations) {
    const control = button(chat.title, () => {
      if (!busy) selectChat(chat.id).catch(error => report(error.message));
    });
    control.dataset.chat = chat.id;
    control.setAttribute('aria-current', String(chat.id === selected));
    history.append(control);
  }
  historyOffset += result.conversations.length;
  byId('more-chats').hidden = !result.more;
}
async function selectChat(id) {
  selected = id;
  localSelection(id);
  pending = undefined;
  reconcileRequest = undefined;
  stopped = false;
  await reloadChat();
  for (const item of history.children) item.setAttribute('aria-current', String(item.dataset.chat === id));
}
async function reloadChat() {
  const id = selected;
  if (!id) {
    current = undefined;
    displayChat();
    return;
  }
  const result = await api(`/api/conversations/${id}`);
  if (id !== selected) return;
  current = result;
  if (lastTurn()?.requestId === reconcileRequest) {
    reconcileRequest = undefined;
    pending = undefined;
  }
  if (lastTurn()?.status !== 'running') stopped = false;
  displayChat();
}
async function newChat() {
  const chat = await api('/api/conversations', 'POST');
  await selectChat(chat.id);
  await refreshHistory();
  return chat.id;
}
async function healthCheck() {
  try {
    const response = await fetch('/api/status', {signal: AbortSignal.timeout(8000)});
    const health = await response.json();
    ready = response.ok && health.status === 'ready';
    voiceReady = health.transcriptionAvailable === true;
    byId('runtimeModel').textContent = health.model || 'Unknown';
    unavailable = ready ? 'Local runtime ready'
      : !health.ollama ? 'Ollama is unavailable'
      : !health.modelInstalled ? 'The selected model is unavailable'
      : 'Eve or its bridge is unavailable';
  } catch {
    ready = false;
    byId('runtimeModel').textContent = 'Unknown';
    unavailable = 'Burito web server is unavailable';
  }
  byId('runtimeSummary').textContent = unavailable;
  if (!voiceReady && !mediaRecorder && !voiceBusy) byId('voice-status').textContent = 'Local transcription is not configured';
  const pill = document.querySelector('.connection-card .pill');
  pill.textContent = ready ? 'Local ready' : 'Unavailable';
  pill.classList.toggle('neutral', ready);
  pill.classList.toggle('amber', !ready);
  if (!busy) {
    if (reconcileRequest || lastTurn()?.status === 'running') {
      try { await reloadChat(); } catch { /* Keep the last visible state while disconnected. */ }
    }
    status.textContent = lastTurn()?.status === 'running' ? 'Reply in progress' : unavailable;
  }
  updateControls();
}

async function readEvents(response, onEvent) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let pendingLine = '';
  try {
    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      pendingLine += decoder.decode(value, {stream: true});
      const lines = pendingLine.split('\n');
      pendingLine = lines.pop();
      for (const line of lines) {
        if (line) onEvent(JSON.parse(line));
      }
    }
    if (pendingLine) throw Error('The streaming response ended mid-event.');
  } finally {
    reader.releaseLock();
  }
}
async function runTurn(payload) {
  busy = true;
  stopped = false;
  activeRequest = undefined;
  updateControls();
  let complete = false;
  let accepted = false;
  let receivedReply = '';
  if (payload.message) appendMessage('user', payload.message);
  const live = appendMessage('assistant', 'Thinking…', true);
  status.textContent = 'Thinking';
  report('');
  try {
    const response = await fetch('/api/turns', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload), signal: AbortSignal.timeout(150000),
    });
    if (!response.ok || !response.headers.get('content-type')?.includes('ndjson')) {
      const result = await response.json();
      if (!result.duplicate && !result.restricted) throw Error(result.error || 'Could not start the reply.');
      if (result.restricted) {
        live.textContent = result.reply;
        status.textContent = 'Desktop action unavailable';
      }
      accepted = true;
      complete = true;
    } else {
      await readEvents(response, event => {
        switch (event.type) {
          case 'start':
            accepted = true;
            activeRequest = payload.requestId;
            updateControls();
            pending = undefined;
            metrics.textContent = `History included ${event.contextBytes} / ${event.contextBudgetBytes} bytes`;
            break;
          case 'delta':
            receivedReply += event.text;
            live.textContent = receivedReply;
            if (status.textContent !== 'Responding') status.textContent = 'Responding';
            conversation.scrollTop = conversation.scrollHeight;
            break;
          case 'tool':
            status.textContent = 'Runtime tool execution';
            break;
          case 'approval':
            status.textContent = 'Approval required';
            report('This web session cannot authorize runtime actions.');
            break;
          case 'done':
            complete = true;
            live.textContent = event.reply || event.detail || '';
            status.textContent = event.status === 'completed' ? 'Reply complete'
              : event.status === 'cancelled' ? 'Reply stopped' : 'Reply failed';
            if (event.detail) report(event.detail);
            else if (event.metrics?.finishReason === 'length') report('The model reached its response length limit.');
            if (event.notificationAccepted === false) report('The desktop notification could not be delivered.');
            displayMetrics(event.metrics);
            break;
        }
      });
    }
    if (!complete) throw Error('The connection ended. Checking the saved turn.');
  } catch (error) {
    status.textContent = 'Chat interrupted';
    report(error.message);
    reconcileRequest = payload.requestId;
    if (!accepted) pending = payload;
  } finally {
    busy = false;
    activeRequest = undefined;
    try {
      await reloadChat();
      if (lastTurn()?.requestId === payload.requestId) pending = undefined;
      await refreshHistory();
    } catch {
      // Preserve the visible partial reply and let the health poll reconnect.
    }
    updateControls();
    input.focus();
  }
}

function releaseMicrophone() {
  clearTimeout(voiceTimer);
  voiceTimer = undefined;
  for (const track of voiceStream?.getTracks() ?? []) track.stop();
  voiceStream = undefined;
  byId('record-voice').setAttribute('aria-pressed', 'false');
  byId('record-voice').textContent = 'Record voice';
  byId('cancel-voice').hidden = true;
}

async function transcribeRecording(blob) {
  voiceBusy = true;
  byId('voice-status').textContent = 'Transcribing locally…';
  updateControls();
  try {
    const language = byId('voice-language').value;
    const response = await fetch(`/api/transcribe?language=${encodeURIComponent(language)}`, {
      method: 'POST',
      headers: {'Content-Type': blob.type || 'audio/webm'},
      body: blob,
      signal: AbortSignal.timeout(60000),
    });
    const result = await response.json();
    if (!response.ok) throw Error(result.error || `Transcription failed (${response.status}).`);
    if (result.text) {
      input.value = input.value.trim() ? `${input.value.trim()} ${result.text}` : result.text;
    }
    byId('voice-status').textContent = result.text
      ? 'Transcript ready to review and edit; it has not been sent.'
      : 'No speech detected. Nothing was sent.';
    input.focus();
  } catch (error) {
    byId('voice-status').textContent = 'Transcription failed';
    report(error.message);
  } finally {
    voiceBusy = false;
    updateControls();
  }
}

function finishRecording(discard = false) {
  if (!mediaRecorder) return;
  discardVoice = discard;
  clearTimeout(voiceTimer);
  byId('cancel-voice').hidden = true;
  if (!discard) byId('voice-status').textContent = 'Recording stopped; processing locally…';
  if (mediaRecorder.state !== 'inactive') mediaRecorder.stop();
}

async function startRecording() {
  if (voiceStarting || mediaRecorder || busy || voiceBusy) return;
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    byId('voice-status').textContent = 'This browser does not support microphone recording.';
    return;
  }
  voiceStarting = true;
  cancelVoiceStart = false;
  byId('cancel-voice').hidden = false;
  updateControls();
  byId('voice-status').textContent = 'Waiting for browser microphone permission…';
  try {
    voiceStream = await navigator.mediaDevices.getUserMedia({
      audio: {echoCancellation: true, noiseSuppression: true, autoGainControl: true},
      video: false,
    });
  } catch (error) {
    byId('voice-status').textContent = error.name === 'NotAllowedError'
      ? 'Microphone permission was denied.'
      : error.name === 'NotFoundError' ? 'No microphone is available to the browser.'
        : 'Could not open the microphone.';
    report(byId('voice-status').textContent);
    voiceStarting = false;
    byId('cancel-voice').hidden = true;
    updateControls();
    return;
  }
  if (cancelVoiceStart) {
    for (const track of voiceStream.getTracks()) track.stop();
    voiceStream = undefined;
    voiceStarting = false;
    byId('cancel-voice').hidden = true;
    byId('voice-status').textContent = 'Microphone request cancelled.';
    updateControls();
    return;
  }
  const mimeType = ['audio/webm;codecs=opus', 'audio/ogg;codecs=opus', 'audio/webm']
    .find(type => MediaRecorder.isTypeSupported(type));
  try {
    mediaRecorder = new MediaRecorder(voiceStream, mimeType ? {mimeType} : undefined);
  } catch {
    releaseMicrophone();
    voiceStarting = false;
    byId('voice-status').textContent = 'The browser could not start audio recording.';
    updateControls();
    return;
  }
  voiceChunks = [];
  discardVoice = false;
  mediaRecorder.addEventListener('dataavailable', event => {
    if (event.data.size) voiceChunks.push(event.data);
  });
  mediaRecorder.addEventListener('stop', () => {
    const recorder = mediaRecorder;
    mediaRecorder = undefined;
    const chunks = voiceChunks;
    voiceChunks = [];
    releaseMicrophone();
    updateControls();
    if (discardVoice) {
      byId('voice-status').textContent = 'Recording discarded.';
      return;
    }
    const blob = new Blob(chunks, {type: recorder.mimeType || 'audio/webm'});
    chunks.length = 0;
    if (!blob.size || blob.size > 8 * 1024 * 1024) {
      byId('voice-status').textContent = 'Recording was empty or exceeded the 8 MiB limit.';
      return;
    }
    transcribeRecording(blob);
  }, {once: true});
  mediaRecorder.start(250);
  byId('record-voice').textContent = 'Stop and transcribe';
  byId('record-voice').setAttribute('aria-pressed', 'true');
  byId('cancel-voice').hidden = false;
  byId('voice-status').textContent = 'Recording · microphone active · maximum 15 seconds';
  voiceStarting = false;
  updateControls();
  voiceTimer = setTimeout(() => finishRecording(false), 15_000);
}

byId('record-voice').addEventListener('click', () => {
  if (mediaRecorder) finishRecording(false);
  else startRecording();
});
byId('cancel-voice').addEventListener('click', () => {
  if (voiceStarting) {
    cancelVoiceStart = true;
    byId('cancel-voice').hidden = true;
    byId('voice-status').textContent = 'Cancelling microphone request…';
  } else finishRecording(true);
});

composer.addEventListener('submit', async event => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text || busy || !ready) return;
  if (new TextEncoder().encode(text).length > 2400) return report('Use up to 2,400 UTF-8 bytes per message.');
  // Disable the composer while the initial conversation is being created.
  busy = true;
  updateControls();
  try {
    const id = selected || await newChat();
    input.value = '';
    await runTurn({conversation: id, requestId: requestId(), message: text});
  } catch (error) {
    report(error.message);
  } finally {
    busy = false;
    updateControls();
  }
});
stop.addEventListener('click', async () => {
  stopped = true;
  updateControls();
  try {
    await api('/api/stop', 'POST', {conversation: selected, requestId: activeRequest || lastTurn()?.requestId});
    if (busy || lastTurn()?.status === 'running') status.textContent = 'Stopping';
  } catch (error) {
    stopped = false;
    updateControls();
    report(error.message);
  }
});
retry.addEventListener('click', () => {
  if (busy || !ready) return;
  if (pending) return runTurn(pending);
  if (lastTurn()) return runTurn({conversation: selected, requestId: requestId(), retry: lastTurn().id});
});
byId('new-chat').addEventListener('click', () => newChat().then(() => input.focus()).catch(error => report(error.message)));
byId('rename-chat').addEventListener('click', async () => {
  const id = selected;
  const title = window.prompt('Conversation title', current?.title || '');
  if (!title?.trim()) return;
  try {
    await api(`/api/conversations/${id}`, 'PATCH', {title});
    await reloadChat();
    await refreshHistory();
  } catch (error) { report(error.message); }
});
byId('delete-chat').addEventListener('click', async () => {
  const id = selected;
  if (!window.confirm('Delete this conversation and its messages?')) return;
  try {
    await api(`/api/conversations/${id}`, 'DELETE');
    await selectChat(null);
    await refreshHistory();
  } catch (error) { report(error.message); }
});
byId('older-turns').addEventListener('click', async () => {
  const id = selected;
  try {
    const previous = await api(`/api/conversations/${id}?before=${current.before}`);
    if (selected === id) {
      current.turns.unshift(...previous.turns);
      current.before = previous.before;
      displayChat();
      conversation.scrollTop = 0;
    }
  } catch (error) { report(error.message); }
});
let searchTimeout;
search.addEventListener('input', () => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => refreshHistory().catch(error => report(error.message)), 200);
});
byId('more-chats').addEventListener('click', () => refreshHistory(true).catch(error => report(error.message)));

async function settings() {
  const data = await api('/api/personality');
  const form = byId('personality');
  for (const [key, values] of Object.entries(data.options)) {
    const label = document.createElement('label');
    label.textContent = {tone: 'Tone', length: 'Reply length', formality: 'Formality', depth: 'Technical depth',
      humor: 'Humor', style: 'Style'}[key];
    const select = document.createElement('select');
    select.name = key;
    for (const value of values) select.add(new Option(value, value, false, data.settings[key] === value));
    label.append(select);
    form.append(label);
  }
  const save = document.createElement('button');
  save.type = 'submit';
  save.textContent = 'Save personality';
  form.append(save);
  form.addEventListener('submit', async event => {
    event.preventDefault();
    try {
      await api('/api/personality', 'POST', Object.fromEntries(new FormData(form)));
      report('Personality saved for future replies.');
    } catch (error) { report(error.message); }
  });
}

function tick() {
  const now = new Date();
  byId('clock').textContent = now.toLocaleTimeString([], {hour12: false});
  byId('date').textContent = now.toLocaleDateString([], {year: 'numeric', month: 'short', day: '2-digit'});
}
document.querySelectorAll('[data-nav]').forEach(control => control.addEventListener('click', () => {
  const target = byId(control.dataset.nav);
  if (target?.tagName === 'DETAILS') target.open = true;
  if (target) target.scrollIntoView({block: 'nearest'});
}));

tick();
setInterval(tick, 1000);
updateControls();
healthCheck();
setInterval(healthCheck, 5000);
refreshHistory().then(async () => {
  const id = getSelection() ?? history.firstElementChild?.dataset.chat;
  if (id) {
    try { await selectChat(id); } catch { await selectChat(null); }
  }
}).catch(error => report(error.message));
settings().catch(error => report(error.message));
