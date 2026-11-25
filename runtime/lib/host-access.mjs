import { execFile } from 'node:child_process';
import { readSettings } from './settings.mjs';

export async function hostAccess(request, signal, approvedAction = false) {
  // Enforce local mode and the owner's access switch outside the model prompt.
  readSettings(process.env);
  if (process.env.BURITO_PC_ACCESS === '0') throw new Error('PC file/application tools are disabled for this chat.');
  if ((request.action === 'screen_read' || request.action === 'screen_reserve') && process.env.BURITO_SCREEN_READ !== '1') {
    throw new Error('On-demand screen reading is disabled for this chat.');
  }
  if ((request.action === 'windows' || request.action === 'focus_window' || request.action === 'inspect_window') && process.env.BURITO_DESKTOP_CONTROL !== '1') {
    throw new Error('Desktop window access is disabled for this chat.');
  }
  if (request.action === 'desktop_insert_text' && process.env.BURITO_DESKTOP_CONTROL !== '1') {
    throw new Error('Native text insertion is disabled; start with --enable-desktop-control.');
  }
  if (request.action === 'clipboard_write_text' && process.env.BURITO_DESKTOP_CONTROL !== '1') {
    throw new Error('Desktop clipboard writing is disabled; start with --enable-desktop-control.');
  }
  if (request.action === 'browser_search' && process.env.BURITO_BROWSER_SEARCH !== '1') {
    throw new Error('Approval-gated Brave search is disabled for this chat.');
  }
  if (['browser_tabs', 'browser_find_tabs', 'browser_activate_tab'].includes(request.action) && process.env.BURITO_BRAVE_TABS !== '1') {
    throw new Error('Approval-gated Brave tab count is disabled for this chat.');
  }
  if (['browser_read_page', 'browser_page_action', 'browser_copy_text'].includes(request.action) && process.env.BURITO_BROWSER_CONTROL !== '1') {
    throw new Error('Approval-gated Brave page access is disabled for this chat.');
  }
  if (!process.env.BURITO_PROJECT_ROOT || !process.env.BURITO_PYTHON) {
    throw new Error('Start with python3 -m burito chat to configure the local bridge.');
  }
  return new Promise((resolve, reject) => {
    const timeout = ['screen_read', 'inspect_window', 'browser_search', 'browser_read_page'].includes(request.action) ? 90000
      : request.action === 'desktop_insert_text' ? 30000
      : ['windows', 'focus_window'].includes(request.action) ? 30000 : 15000;
    const child = execFile(process.env.BURITO_PYTHON, ['-m', 'burito', 'access-bridge'], {
      cwd: process.env.BURITO_PROJECT_ROOT,
      env: { ...process.env, BURITO_APPROVED_APP_LAUNCH: request.action === 'launch' && approvedAction ? '1' : '0',
        BURITO_APPROVED_BROWSER_SEARCH: request.action === 'browser_search' && approvedAction ? '1' : '0',
        BURITO_APPROVED_BROWSER_TABS: ['browser_tabs', 'browser_find_tabs', 'browser_activate_tab'].includes(request.action) && approvedAction ? '1' : '0',
        BURITO_APPROVED_BROWSER_CONTROL: ['browser_read_page', 'browser_page_action', 'browser_copy_text'].includes(request.action) && approvedAction ? '1' : '0',
        BURITO_APPROVED_WINDOW_FOCUS: ['focus_window', 'inspect_window'].includes(request.action) && approvedAction ? '1' : '0',
        BURITO_APPROVED_DESKTOP_TEXT: request.action === 'desktop_insert_text' && approvedAction ? '1' : '0',
        BURITO_APPROVED_CLIPBOARD_WRITE: request.action === 'clipboard_write_text' && approvedAction ? '1' : '0' },
      timeout, maxBuffer: 131072, signal,
    }, (error, stdout, stderr) => {
      if (error) return reject(new Error(stderr.trim().slice(-3000) || error.message));
      try { resolve(JSON.parse(stdout)); } catch { reject(new Error('Local bridge returned invalid JSON.')); }
    });
    child.stdin.on('error', () => {});
    child.stdin.end(JSON.stringify(request));
  });
}
