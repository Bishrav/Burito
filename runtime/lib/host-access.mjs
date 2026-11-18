import { execFile } from 'node:child_process';
import { readSettings } from './settings.mjs';

export async function hostAccess(request, signal, approvedLaunch = false) {
  // Enforce local mode and the owner's access switch outside the model prompt.
  readSettings(process.env);
  if (process.env.BURITO_PC_ACCESS === '0') throw new Error('PC file/application tools are disabled for this chat.');
  if ((request.action === 'screen_read' || request.action === 'screen_reserve') && process.env.BURITO_SCREEN_READ !== '1') {
    throw new Error('On-demand screen reading is disabled for this chat.');
  }
  if ((request.action === 'windows' || request.action === 'focus_window' || request.action === 'inspect_window') && process.env.BURITO_DESKTOP_CONTROL !== '1') {
    throw new Error('Desktop window access is disabled for this chat.');
  }
  if (!process.env.BURITO_PROJECT_ROOT || !process.env.BURITO_PYTHON) {
    throw new Error('Start with python3 -m burito chat to configure the local bridge.');
  }
  return new Promise((resolve, reject) => {
    const timeout = ['screen_read', 'inspect_window'].includes(request.action) ? 75000
      : ['windows', 'focus_window'].includes(request.action) ? 30000 : 15000;
    const child = execFile(process.env.BURITO_PYTHON, ['-m', 'burito', 'access-bridge'], {
      cwd: process.env.BURITO_PROJECT_ROOT,
      env: { ...process.env, BURITO_APPROVED_APP_LAUNCH: approvedLaunch ? '1' : '0',
        BURITO_APPROVED_WINDOW_FOCUS: ['focus_window', 'inspect_window'].includes(request.action) && approvedLaunch ? '1' : '0' },
      timeout, maxBuffer: 65536, signal,
    }, (error, stdout, stderr) => {
      if (error) return reject(new Error(stderr.trim().slice(0, 500) || error.message));
      try { resolve(JSON.parse(stdout)); } catch { reject(new Error('Local bridge returned invalid JSON.')); }
    });
    child.stdin.on('error', () => {});
    child.stdin.end(JSON.stringify(request));
  });
}
