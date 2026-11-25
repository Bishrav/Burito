// Sends tab counts by default. Titles and visible page text are returned only
// for an approved Burito request, over the local Native Messaging connection.
const HOST = 'com.burito.brave_tabs';
let port;
let refreshTimer;
let reconnectTimer;
let pollTimer;

function send(message) {
  if (!port) return;
  try { port.postMessage(message); } catch { /* reconnect handles closed ports */ }
}

function publishCount() {
  if (!port) return;
  chrome.tabs.query({}, (tabs) => {
    if (chrome.runtime.lastError) return;
    send({ type: 'tab_count', count: tabs.length });
  });
}

function callChrome(run) {
  return new Promise((resolve, reject) => run((value) => {
    const error = chrome.runtime.lastError;
    if (error) reject(new Error(error.message));
    else resolve(value);
  }));
}

async function writeClipboard(text) {
  if (!await chrome.permissions.contains({ permissions: ['clipboardWrite'] })) {
    throw new Error('Enable clipboard copy from the Burito extension popup first.');
  }
  const documentUrl = chrome.runtime.getURL('offscreen.html');
  let exists;
  if (chrome.runtime.getContexts) {
    const contexts = await chrome.runtime.getContexts({
      contextTypes: ['OFFSCREEN_DOCUMENT'], documentUrls: [documentUrl],
    });
    exists = contexts.length > 0;
  } else {
    const openClients = await clients.matchAll();
    exists = openClients.some((client) => client.url === documentUrl);
  }
  if (!exists) {
    await chrome.offscreen.createDocument({
      url: 'offscreen.html',
      reasons: ['CLIPBOARD'],
      justification: 'Write the exact text approved by the owner to the system clipboard.',
    });
  }
  try {
    const result = await chrome.runtime.sendMessage({
      target: 'burito-offscreen', type: 'copy-text', text,
    });
    if (!result?.ok) throw new Error(result?.error || 'Clipboard write was not confirmed.');
  } finally {
    await chrome.offscreen.closeDocument().catch(() => {});
  }
}

async function activePermittedPage() {
  if (!await chrome.permissions.contains({ permissions: ['scripting'] })) {
    throw new Error('Enable page access from the Burito extension popup first.');
  }
  const tabs = await callChrome((done) => chrome.tabs.query({ active: true, lastFocusedWindow: true }, done));
  const tab = tabs?.[0];
  let url;
  try { url = new URL(tab?.url || ''); } catch { /* reject below */ }
  if (!tab || !url || !['http:', 'https:'].includes(url.protocol)) {
    throw new Error('The active Brave tab is not a regular HTTP or HTTPS page.');
  }
  const origin = `${url.origin}/*`;
  if (!await chrome.permissions.contains({ origins: [origin] })) {
    throw new Error(`Enable ${url.host} or all HTTP/HTTPS websites in the Burito extension popup first.`);
  }
  return { tab, origin };
}

async function navigateActiveTab(rawUrl) {
  let target;
  try { target = new URL(rawUrl); } catch { throw new Error('That is not a valid URL.'); }
  if (!['http:', 'https:'].includes(target.protocol) || !target.hostname || target.username || target.password) {
    throw new Error('Only HTTP/HTTPS URLs without embedded credentials can be opened.');
  }
  const tabs = await callChrome((done) => chrome.tabs.query({ active: true, lastFocusedWindow: true }, done));
  const tab = tabs?.[0];
  if (!tab || tab.id === undefined) throw new Error('No active Brave tab is available.');
  const loaded = new Promise((resolve) => {
    let finished = false;
    const finish = (complete) => {
      if (finished) return;
      finished = true;
      clearTimeout(timer);
      chrome.tabs.onUpdated.removeListener(listener);
      resolve(complete);
    };
    const listener = (changedId, info) => {
      if (changedId === tab.id && info.status === 'complete') finish(true);
    };
    const timer = setTimeout(() => finish(false), 8000);
    chrome.tabs.onUpdated.addListener(listener);
  });
  await callChrome((done) => chrome.tabs.update(tab.id, { url: target.href }, done));
  return { status: 'navigation_requested', load_complete: await loaded, host: target.host };
}

function readVisiblePage() {
  const text = document.body?.innerText || '';
  const visible = (element) => {
    const style = getComputedStyle(element);
    return element.getClientRects().length > 0 && style.visibility !== 'hidden' && style.display !== 'none';
  };
  const label = (element) => ([element.getAttribute('aria-label'), element.getAttribute('title'),
    element.getAttribute('placeholder'), element.labels ? [...element.labels].map((item) => item.innerText).join(' ') : '',
    element.innerText, element.value].filter(Boolean).join(' ')).trim().replace(/\s+/g, ' ').slice(0, 120);
  const clickTargets = [...document.querySelectorAll('a,button,[role="button"],[role="link"],[role="row"],tr.zA,summary')]
    .filter((element) => visible(element) && label(element))
    .slice(0, 50)
    .map((element) => ({ role: element.getAttribute('role') || element.tagName.toLowerCase(), label: label(element) }));
  const videoTargets = [...document.querySelectorAll('a[href*="/watch"],a[href*="/shorts/"]')]
    .filter((element) => visible(element) && label(element))
    .slice(0, 20)
    .map((element) => ({ role: 'video_link', label: label(element) }));
  return { title: document.title || '', text: text.slice(0, 9000), truncated: text.length > 9000,
    click_targets: clickTargets, video_targets: videoTargets };
}

function performPageAction(data) {
  const visible = (element) => {
    const style = getComputedStyle(element);
    return element.getClientRects().length > 0 && style.visibility !== 'hidden' && style.display !== 'none';
  };
  const label = (element) => ([element.getAttribute('aria-label'), element.getAttribute('title'),
    element.getAttribute('placeholder'), element.labels ? [...element.labels].map((item) => item.innerText).join(' ') : '',
    element.innerText, element.value, element.getAttribute('name')].filter(Boolean).join(' '))
    .trim().replace(/\s+/g, ' ').slice(0, 240);
  const findUnique = (selector, phrase) => {
    const rawNeedle = String(phrase || '').trim().toLocaleLowerCase();
    const abbreviated = /(?:…|\.{3})\s*$/.test(rawNeedle);
    const needle = rawNeedle.replace(/(?:…|\.{3})\s*$/u, '').trim();
    const matches = [...document.querySelectorAll(selector)].filter((element) => {
      if (!visible(element)) return false;
      const candidate = label(element).toLocaleLowerCase();
      return candidate.includes(rawNeedle) || (abbreviated && candidate.includes(needle));
    });
    if (!matches.length) throw new Error('No visible control matched that label.');
    const exact = matches.filter((element) => label(element).toLocaleLowerCase() === needle);
    const candidates = (exact.length ? exact : matches).sort((a, b) => {
      const rank = (element) => ['TR'].includes(element.tagName) || element.getAttribute('role') === 'row' ? 1 : 0;
      return rank(a) - rank(b) || label(a).length - label(b).length;
    });
    const sameRank = candidates.length > 1 &&
      (['TR'].includes(candidates[0].tagName) || candidates[0].getAttribute('role') === 'row') ===
      (['TR'].includes(candidates[1].tagName) || candidates[1].getAttribute('role') === 'row');
    if (sameRank && label(candidates[0]).length === label(candidates[1]).length) {
      throw new Error(`More than one visible control matches (${candidates.length}); use a more specific label.`);
    }
    return candidates[0];
  };
  if (data.action === 'scroll') {
    const distance = data.direction === 'up' ? -data.amount : data.amount;
    window.scrollBy({ top: distance, behavior: 'auto' });
    return { status: 'completed', action: 'scroll', scroll_y: Math.round(window.scrollY) };
  }
  if (data.action === 'click_text') {
    const element = findUnique('a,button,[role="button"],[role="menuitem"],[role="link"],[role="row"],tr.zA,summary,input[type="submit"],input[type="button"]', data.target);
    const control = label(element);
    element.click();
    return { status: 'completed', action: 'click_text', control };
  }
  if (data.action === 'type_text' || data.action === 'press_key') {
    const element = findUnique('input,textarea,[contenteditable="true"],[role="textbox"]', data.target);
    const type = (element.getAttribute('type') || '').toLowerCase();
    if (['password', 'file', 'hidden'].includes(type) || element.disabled || element.readOnly) {
      throw new Error('That field is disabled or is a password, file, or hidden field.');
    }
    element.focus();
    if (data.action === 'type_text') {
      if (element.isContentEditable || element.getAttribute('role') === 'textbox') {
        element.textContent = data.text;
      } else {
        const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(element), 'value')?.set;
        if (!setter) throw new Error('This field cannot be safely filled.');
        setter.call(element, data.text);
      }
      element.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: data.text }));
      element.dispatchEvent(new Event('change', { bubbles: true }));
      return { status: 'completed', action: 'type_text', field: label(element), characters: data.text.length };
    }
    element.dispatchEvent(new KeyboardEvent('keydown', { key: data.key, bubbles: true }));
    element.dispatchEvent(new KeyboardEvent('keyup', { key: data.key, bubbles: true }));
    if (data.key === 'Enter' && element.form) element.form.requestSubmit();
    if (data.key === 'Tab') element.blur();
    if (data.key === 'Escape') element.blur();
    return { status: 'completed', action: 'press_key', key: data.key, field: label(element) };
  }
  throw new Error('Unsupported page action.');
}

async function answerCommand(command) {
  const reply = (ok, result, error) => send({ type: 'command_result', request_id: command.request_id, ok, result, error });
  try {
    if (command.command === 'copy_text') {
      const text = command.text;
      if (typeof text !== 'string' || !text || text.length > 5000) {
        throw new Error('Clipboard text must contain 1–5,000 characters.');
      }
      await writeClipboard(text);
      reply(true, { status: 'copied', characters: text.length, scope: 'System clipboard; write-only.' }, undefined);
      return;
    }
    if (['find', 'activate'].includes(command.command) &&
        !await chrome.permissions.contains({ permissions: ['tabs'] })) {
      throw new Error('Enable tab-label access from the Burito extension popup first.');
    }
    if (command.command === 'find') {
      const tabs = await callChrome((done) => chrome.tabs.query({}, done));
      const query = String(command.query || '').trim().toLocaleLowerCase();
      if (!query) throw new Error('A tab-title search phrase is required.');
      const matches = tabs.filter((tab) => typeof tab.title === 'string' && tab.title.toLocaleLowerCase().includes(query))
        .slice(0, 10)
        .map((tab) => ({ tab_id: tab.id, title: tab.title.slice(0, 512), window_id: tab.windowId, active: Boolean(tab.active) }));
      reply(true, { tabs: matches }, undefined);
      return;
    }
    if (command.command === 'activate') {
      if (!Number.isInteger(command.tab_id) || typeof command.expected_title !== 'string') throw new Error('Invalid tab selection.');
      const tab = await callChrome((done) => chrome.tabs.get(command.tab_id, done));
      if (!tab || tab.title !== command.expected_title) throw new Error('That Brave tab no longer exists with the approved title; find it again.');
      await callChrome((done) => chrome.windows.update(tab.windowId, { focused: true }, done));
      const activated = await callChrome((done) => chrome.tabs.update(tab.id, { active: true }, done));
      if (!activated || !activated.active) throw new Error('Brave did not confirm that the requested tab became active.');
      reply(true, { status: 'activated', tab_id: tab.id, title: tab.title }, undefined);
      return;
    }
    if (command.command === 'read_page' || command.command === 'page_action') {
      const data = command.data;
      if (command.command === 'page_action' && data?.action === 'navigate') {
        reply(true, await navigateActiveTab(data.url), undefined);
        return;
      }
      const { tab } = await activePermittedPage();
      if (command.command === 'read_page') {
        const executions = await callChrome((done) => chrome.scripting.executeScript({ target: { tabId: tab.id }, func: readVisiblePage }, done));
        const page = executions?.[0]?.result;
        if (!page || typeof page.text !== 'string') throw new Error('Brave returned no readable page content.');
        reply(true, page, undefined);
        return;
      }
      if (!data || typeof data !== 'object') throw new Error('Invalid browser action.');
      if (data.action === 'back' || data.action === 'forward') {
        await callChrome((done) => chrome.tabs[data.action === 'back' ? 'goBack' : 'goForward'](tab.id, done));
        reply(true, { status: 'completed', action: data.action }, undefined);
        return;
      }
      const executions = await callChrome((done) => chrome.scripting.executeScript({
        target: { tabId: tab.id }, func: performPageAction, args: [data],
      }, done));
      const outcome = executions?.[0]?.result;
      if (!outcome || outcome.status !== 'completed') throw new Error('Brave did not confirm the page action.');
      reply(true, outcome, undefined);
      return;
    }
    throw new Error('Unsupported Burito tab command.');
  } catch (error) {
    reply(false, undefined, String(error?.message || error).slice(0, 300));
  }
}

function pollCommand() {
  send({ type: 'poll' });
}

function schedulePublish() {
  clearTimeout(refreshTimer);
  refreshTimer = setTimeout(publishCount, 100);
}

function connect() {
  clearTimeout(reconnectTimer);
  try { port = chrome.runtime.connectNative(HOST); }
  catch { port = undefined; reconnectTimer = setTimeout(connect, 3000); return; }
  port.onMessage.addListener((message) => {
    if (message?.type === 'command') void answerCommand(message);
  });
  port.onDisconnect.addListener(() => {
    port = undefined;
    reconnectTimer = setTimeout(connect, 3000);
  });
  clearInterval(pollTimer);
  pollTimer = setInterval(pollCommand, 300);
  pollCommand();
  publishCount();
}

chrome.tabs.onCreated.addListener(schedulePublish);
chrome.tabs.onRemoved.addListener(schedulePublish);
chrome.windows.onCreated.addListener(schedulePublish);
chrome.windows.onRemoved.addListener(schedulePublish);
chrome.runtime.onStartup.addListener(schedulePublish);
chrome.runtime.onInstalled.addListener(schedulePublish);
setInterval(publishCount, 5000);
connect();