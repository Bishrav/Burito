chrome.tabs.query({}, (tabs) => {
  const count = document.getElementById('count');
  if (chrome.runtime.lastError) {
    count.textContent = 'Unavailable';
    return;
  }
  count.textContent = String(tabs.length);
});

const enable = document.getElementById('enable');
const enableSite = document.getElementById('enable-site');
const enableAll = document.getElementById('enable-all');
const enableCopy = document.getElementById('enable-copy');
const status = document.getElementById('status');
chrome.permissions.contains({ permissions: ['tabs'] }, (granted) => {
  if (granted) {
    enable.textContent = 'Tab labels enabled';
    enable.disabled = true;
  }
});

chrome.permissions.contains({ permissions: ['clipboardWrite'] }, (granted) => {
  if (granted) {
    enableCopy.textContent = 'Clipboard copy enabled';
    enableCopy.disabled = true;
    status.textContent = 'Burito can write exact text only after each copy approval. Clipboard reading is not enabled.';
  }
});
enableCopy.addEventListener('click', () => {
  chrome.permissions.request({ permissions: ['clipboardWrite'] }, (granted) => {
    status.textContent = granted
      ? 'Clipboard copy enabled. Burito still asks before every exact-text copy; clipboard reading is not enabled.'
      : 'Clipboard permission not granted. Burito cannot copy text into the system clipboard.';
    if (granted) {
      enableCopy.textContent = 'Clipboard copy enabled';
      enableCopy.disabled = true;
    }
  });
});
enable.addEventListener('click', () => {
  chrome.permissions.request({ permissions: ['tabs'] }, (granted) => {
    status.textContent = granted ? 'Tab labels enabled. Burito asks before each lookup.' : 'Permission not granted; tab titles remain unavailable.';
    if (granted) {
      enable.textContent = 'Tab labels enabled';
      enable.disabled = true;
    }
  });
});

const allWebOrigins = ['http://*/*', 'https://*/*'];
chrome.permissions.contains({ permissions: ['scripting'], origins: allWebOrigins }, (granted) => {
  if (granted) {
    enableAll.textContent = 'All websites enabled';
    enableAll.disabled = true;
    status.textContent = 'Burito can access regular HTTP/HTTPS sites. Each page read or action still requires Burito approval.';
  }
});

enableAll.addEventListener('click', () => {
  chrome.permissions.request({ permissions: ['scripting'], origins: allWebOrigins }, (granted) => {
    if (granted) {
      enableAll.textContent = 'All websites enabled';
      enableAll.disabled = true;
      status.textContent = 'Enabled for regular HTTP/HTTPS sites. Burito still asks before each page read or action.';
    } else {
      status.textContent = 'Permission not granted. Burito can still be enabled one site at a time.';
    }
  });
});

enableSite.addEventListener('click', () => {
  chrome.permissions.contains({ permissions: ['tabs'] }, (hasTabs) => {
    if (!hasTabs) {
      status.textContent = 'Enable tab labels first to grant access to one site, or choose Enable all websites.';
      return;
    }
    chrome.tabs.query({ active: true, lastFocusedWindow: true }, (tabs) => {
      const active = tabs?.[0];
      let url;
      try { url = new URL(active?.url || ''); } catch { /* handled below */ }
      if (!url || !['http:', 'https:'].includes(url.protocol)) {
        status.textContent = 'Open a regular HTTP or HTTPS page first.';
        return;
      }
      const origin = `${url.origin}/*`;
      chrome.permissions.request({ permissions: ['scripting'], origins: [origin] }, (granted) => {
        status.textContent = granted
          ? `Approved for ${url.host}. Burito still asks before each read or action.`
          : `Site permission not granted for ${url.host}.`;
      });
    });
  });
});