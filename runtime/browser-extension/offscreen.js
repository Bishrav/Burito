chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.target !== 'burito-offscreen' || message?.type !== 'copy-text') return;
  if (typeof message.text !== 'string' || !message.text || message.text.length > 5000) {
    sendResponse({ ok: false, error: 'Clipboard text must contain 1–5,000 characters.' });
    return;
  }
  (async () => {
    try {
      await navigator.clipboard.writeText(message.text);
      sendResponse({ ok: true });
    } catch {
      const area = document.createElement('textarea');
      area.value = message.text;
      area.setAttribute('readonly', '');
      area.style.position = 'fixed';
      area.style.opacity = '0';
      document.body.append(area);
      area.select();
      let ok = false;
      try { ok = document.execCommand('copy'); } catch { /* report below */ }
      area.remove();
      sendResponse(ok ? { ok: true } : { ok: false, error: 'The browser rejected the clipboard write.' });
    }
  })();
  return true;
});
